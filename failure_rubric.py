"""Failure analysis of the extraction-rubric experiment (experiment 14): what breaks, and at which stage.

Stages examined, in pipeline order:
  1. extraction   GPT-5.6 checks a random sample of extracted records against the source paper (target-free):
                  is each field supported, distorted or unsupported, and is it the authors' own work?
  2. retrieval    are records that anticipate the target (evidence-ceiling ratings) in the packed context?
  3. use          are those records cited, and does citing them go with better hypotheses?
  4. reasoning    judge fatal errors coded into the failure-analysis taxonomy (GPT-5.6), plus the audit labels
  5. generation   the reproducible closed-book format failure, reproduced with the raw model output captured

Diagnostic stages read the judge outputs and ceiling ratings (which used the hidden target); nothing here feeds
back into any generation.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import requests

import llm_client as lc
import rubric_eval as rx
from failure_analysis import CODER_SYSTEM, ERROR_CATEGORIES, spearman, validate_labels
from hypothesis_evidence_v2 import atomic_json
from temporal_eval_v3 import ALL_DIMENSIONS, PRIMARY_DIMENSIONS, QUERY_LEVELS
from temporal_hypothesis_benchmark import _GENERATE_SYSTEM, _read_json

OUT = rx.OUT / "failure"
FIDELITY_SAMPLE = 40
FAIL_THRESHOLD = 1.0
EVIDENCE_ARMS = tuple(a for a in rx.ARMS if a != "closed_book")
VERDICTS = ("supported", "distorted", "unsupported")
OWNERSHIP = ("own_work", "cited_work", "mixed")

FIDELITY_SYSTEM = (
    "You check one record that was extracted from a research paper against the paper itself. The input has the "
    "paper text and the record's fields. For every field, judge whether the paper supports it: supported (stated or "
    "directly implied by the paper), distorted (related to the paper but wrong in a number, direction, alloy system, "
    "condition or scope), or unsupported (not in the paper). Also judge ownership: own_work if the record reports "
    "this paper's own results or arguments, cited_work if it reports results the paper attributes to other work, "
    "mixed if both. Return JSON {\"fields\": [{\"field\": str, \"verdict\": str, \"note\": str}], "
    "\"ownership\": str}. Give a short note only for distorted or unsupported fields."
)


def judged_runs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    runs = rx.load_runs()
    gpt = {p.stem: _read_json(p) for p in sorted((rx.OUT / "judgments" / "gpt56").glob("*.json"))}
    return runs, gpt


# ---------------------------------------------------------------- stage: error coding

def code_errors(workers: int, resume: bool) -> dict[str, int]:
    out = OUT / "error_codes"
    _, gpt = judged_runs()
    jobs = [(rid, (rid, j)) for rid, j in gpt.items()
            if j.get("fatal_errors") and not (resume and (out / f"{rid}.json").exists())]

    def job(rid: str, judgment: dict[str, Any]) -> None:
        errors = [str(e) for e in judgment["fatal_errors"]]
        raw = lc.judge_chat_json(CODER_SYSTEM, json.dumps(
            {"errors": [{"index": i, "text": t} for i, t in enumerate(errors)]}, ensure_ascii=False), max_tokens=6000)
        labels = validate_labels(raw, len(errors))
        atomic_json(out / f"{rid}.json", {"run_id": rid, "coder": lc.judge_info(),
                                          "errors": [{"text": t, "category": labels[i]} for i, t in enumerate(errors)]})

    return rx.run_jobs("fa_code", jobs, job, workers)


# ---------------------------------------------------------------- stage: extraction fidelity

def fidelity_sample() -> list[tuple[str, str, dict[str, Any]]]:
    rng = random.Random(20261023)
    picked = []
    for rubric in rx.RUBRICS:
        pool = []
        for path in sorted((rx.OUT / "extractions" / rubric).glob("PMC*.json")):
            payload = _read_json(path)
            for record in payload["records"]:
                pool.append((rubric, payload["paper_id"], record))
        rng.shuffle(pool)
        picked += pool[:FIDELITY_SAMPLE]
    return picked


def source_window(paper_id: str, part: str) -> str:
    text = rx.strip_back_matter((rx.TEXT_DIR / f"{paper_id}.txt").read_text())
    parts = rx.windows(text)
    try:
        index = int(part.split("/")[0]) - 1
    except (ValueError, AttributeError):
        index = 0
    return parts[max(0, min(index, len(parts) - 1))]


def fidelity(workers: int, resume: bool) -> dict[str, int]:
    out = OUT / "fidelity"
    jobs = []
    for rubric, paper_id, record in fidelity_sample():
        name = record["record_id"].replace("::", "__")
        if not (resume and (out / f"{name}.json").exists()):
            jobs.append((name, (name, rubric, paper_id, record)))

    def job(name: str, rubric: str, paper_id: str, record: dict[str, Any]) -> None:
        item = record["item"]
        fields = {f: item.get(f) for _, f in rx.RENDER_FIELDS[rubric]
                  if rx._field_text(item.get(f)) and rx._field_text(item.get(f)).lower() != "not stated"}
        payload = {"paper_text": source_window(paper_id, str(item.get("part", "1/1"))), "record_fields": fields}
        raw = lc.judge_chat_json(FIDELITY_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=8000)
        raw = raw if isinstance(raw, dict) else {}
        verdicts = []
        for entry in raw.get("fields", []) if isinstance(raw.get("fields"), list) else []:
            if isinstance(entry, dict) and str(entry.get("field")) in fields:
                verdict = str(entry.get("verdict", "")).lower()
                verdicts.append({"field": str(entry["field"]),
                                 "verdict": verdict if verdict in VERDICTS else "unsupported",
                                 "note": str(entry.get("note", ""))[:400]})
        ownership = str(raw.get("ownership", "")).lower()
        atomic_json(out / f"{name}.json", {"record_id": record["record_id"], "rubric": rubric, "paper_id": paper_id,
                                           "checker": lc.judge_info(), "fields_checked": sorted(fields),
                                           "verdicts": verdicts,
                                           "ownership": ownership if ownership in OWNERSHIP else "unclear"})

    return rx.run_jobs("fa_fidelity", jobs, job, workers)


# ---------------------------------------------------------------- stage: reproduce generation failure

def reproduce_format_failure(attempts: int = 3) -> dict[str, Any]:
    case = rx.cases()["PMC11375712"]
    query = case["queries"]["broad"]["text"]
    user = json.dumps({"query": query, "knowledge_cutoff": case["publication_date"], "eligible_evidence": []},
                      ensure_ascii=False)
    base = "http://127.0.0.1:8000/v1"
    outputs = []
    for attempt in range(attempts):
        body = {"model": "Qwen3.5-35B-A3B-Q4_K_M.gguf", "max_tokens": 5000,
                "messages": [{"role": "system", "content": _GENERATE_SYSTEM}, {"role": "user", "content": user}],
                "response_format": {"type": "json_object"},
                "chat_template_kwargs": {"enable_thinking": False}}
        response = requests.post(f"{base}/chat/completions", json=body, timeout=600)
        response.raise_for_status()
        choice = response.json()["choices"][0]
        content = choice["message"]["content"]
        try:
            parsed = json.loads(content)
            keys = sorted(parsed) if isinstance(parsed, dict) else type(parsed).__name__
        except json.JSONDecodeError as error:
            parsed, keys = None, f"invalid JSON: {error}"
        outputs.append({"attempt": attempt + 1, "finish_reason": choice.get("finish_reason"),
                        "chars": len(content), "top_level_keys": keys,
                        "has_hypothesis_string": isinstance(parsed, dict)
                        and isinstance(parsed.get("hypothesis"), str) and bool(parsed["hypothesis"].strip()),
                        "head": content[:1500]})
    result = {"paper_id": "PMC11375712", "query_level": "broad", "arm": "closed_book", "query": query,
              "attempts": outputs}
    atomic_json(OUT / "format_failure.json", result)
    return result


# ---------------------------------------------------------------- report

def mean(values: list[Any]) -> float | None:
    values = [v for v in values if v is not None]
    return round(statistics.fmean(values), 3) if values else None


def report() -> dict[str, Any]:
    runs, gpt = judged_runs()
    audits = {p.stem: _read_json(p) for p in sorted((rx.OUT / "audit").glob("*.json"))}
    codes = {p.stem: _read_json(p) for p in sorted((OUT / "error_codes").glob("*.json"))}
    fid = [_read_json(p) for p in sorted((OUT / "fidelity").glob("*.json"))]
    ceilings = {rep: {p.stem: _read_json(p) for p in sorted((rx.OUT / "ceiling" / rep).glob("PMC*.json"))}
                for rep in rx.REPRESENTATIONS}
    supportive = {rep: {pid: {r["record_id"] for r in c["records"]
                              if r["intervention_support"] >= 1 or r["mechanism_support"] >= 1}
                        for pid, c in per.items()} for rep, per in ceilings.items()}
    strong = {rep: {pid: {r["record_id"] for r in c["records"]
                          if r["intervention_support"] == 2 or r["mechanism_support"] == 2}
                    for pid, c in per.items()} for rep, per in ceilings.items()}

    rows = []
    for rid, run in runs.items():
        if rid not in gpt:
            continue
        scores = gpt[rid]["scores"]
        arm = run["arm"]
        sup = supportive.get(arm, {}).get(run["paper_id"], set())
        stg = strong.get(arm, {}).get(run["paper_id"], set())
        packed, cited = set(run["packed_ids"]), set(run["cited_ids"])
        audit = audits.get(rid, {})
        rows.append({
            "rid": rid, "arm": arm, "paper": run["paper_id"], "level": run["query_level"],
            "recon": statistics.fmean(scores[d] for d in PRIMARY_DIMENSIONS), "scores": scores,
            "classification": gpt[rid].get("classification", ""),
            "sup_packed": len(packed & sup), "strong_packed": len(packed & stg),
            "sup_cited": len(cited & sup), "strong_cited": len(cited & stg),
            "packed": len(packed), "cited": len(cited),
            "source": audit.get("mechanism_source"),
            "categories": [e["category"] for e in codes.get(rid, {}).get("errors", [])],
        })
    by_arm = {arm: [r for r in rows if r["arm"] == arm] for arm in rx.ARMS}

    # 1. extraction fidelity
    fidelity_rows: dict[str, Any] = {}
    distortion_notes: dict[str, list[str]] = defaultdict(list)
    for rubric in rx.RUBRICS:
        items = [f for f in fid if f["rubric"] == rubric]
        verdicts = Counter(v["verdict"] for f in items for v in f["verdicts"])
        total = sum(verdicts.values())
        field_bad: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for f in items:
            for v in f["verdicts"]:
                field_bad[v["field"]][1] += 1
                field_bad[v["field"]][0] += v["verdict"] != "supported"
                if v["verdict"] != "supported" and v["note"]:
                    distortion_notes[rubric].append(f"{v['field']}: {v['note']}")
        fidelity_rows[rubric] = {
            "records_checked": len(items), "fields_checked": total,
            "supported": mean([1.0 if v == "supported" else 0.0 for v in verdicts.elements()]),
            "distorted": round(verdicts["distorted"] / max(1, total), 3),
            "unsupported": round(verdicts["unsupported"] / max(1, total), 3),
            "records_fully_supported": mean([1.0 if f["verdicts"] and all(v["verdict"] == "supported"
                                                                         for v in f["verdicts"]) else 0.0
                                             for f in items]),
            "ownership": dict(Counter(f["ownership"] for f in items)),
            "worst_fields": sorted(((k, round(b / n, 2), n) for k, (b, n) in field_bad.items() if n >= 5),
                                   key=lambda x: -x[1])[:3],
        }

    # 2-3. retrieval and use, with success rates
    waterfall = {}
    for arm in EVIDENCE_ARMS:
        rs = by_arm[arm]
        fails = [r for r in rs if r["recon"] <= FAIL_THRESHOLD]
        def stage(r: dict[str, Any]) -> str:
            if r["sup_packed"] == 0:
                return "no_supportive_in_context"
            if r["sup_cited"] == 0:
                return "supportive_in_context_not_cited"
            return "supportive_cited"
        counts_all = Counter(stage(r) for r in rs)
        counts_fail = Counter(stage(r) for r in fails)
        waterfall[arm] = {
            "runs": len(rs), "failures": len(fails), "failure_rate": round(len(fails) / max(1, len(rs)), 3),
            "failure_stage": {k: counts_fail[k] for k in ("no_supportive_in_context",
                                                          "supportive_in_context_not_cited", "supportive_cited")},
            "failure_rate_by_stage": {k: round(sum(1 for r in rs if stage(r) == k and r["recon"] <= FAIL_THRESHOLD)
                                               / counts_all[k], 3) if counts_all[k] else None
                                      for k in ("no_supportive_in_context", "supportive_in_context_not_cited",
                                                "supportive_cited")},
            "runs_by_stage": dict(counts_all),
            "mean_supportive_packed": mean([r["sup_packed"] for r in rs]),
            "mean_strong_packed": mean([r["strong_packed"] for r in rs]),
            "share_supportive_packed_that_is_cited": round(
                sum(r["sup_cited"] for r in rs) / max(1, sum(r["sup_packed"] for r in rs)), 3),
            "share_cited_that_is_supportive": round(
                sum(r["sup_cited"] for r in rs) / max(1, sum(r["cited"] for r in rs)), 3),
        }
    # pooled within-level effect of citing supportive evidence
    use_effect = {}
    for lvl in QUERY_LEVELS:
        rs = [r for r in rows if r["arm"] in EVIDENCE_ARMS and r["level"] == lvl]
        groups = {"no_supportive_in_context": [r for r in rs if r["sup_packed"] == 0],
                  "in_context_not_cited": [r for r in rs if r["sup_packed"] > 0 and r["sup_cited"] == 0],
                  "supportive_cited": [r for r in rs if r["sup_cited"] > 0],
                  "strong_cited": [r for r in rs if r["strong_cited"] > 0]}
        use_effect[lvl] = {k: {"runs": len(v), "recon": mean([r["recon"] for r in v]),
                               "intervention": mean([r["scores"]["intervention_reconstruction"] for r in v]),
                               "mechanism": mean([r["scores"]["mechanism_agreement"] for r in v])}
                           for k, v in groups.items()}

    # 4. reasoning: error categories and mechanism source
    error_mix = {}
    for arm in rx.ARMS:
        counter = Counter(c for r in by_arm[arm] for c in r["categories"])
        total = sum(counter.values())
        error_mix[arm] = {"errors_per_run": round(total / max(1, len(by_arm[arm])), 2),
                          **{c: round(counter[c] / max(1, total), 3) for c in ERROR_CATEGORIES}}
    failure_mix = {}
    for arm in rx.ARMS:
        fails = [r for r in by_arm[arm] if r["recon"] <= FAIL_THRESHOLD]
        counter = Counter(c for r in fails for c in set(r["categories"]))
        failure_mix[arm] = {c: round(counter[c] / max(1, len(fails)), 3) for c in ERROR_CATEGORIES}
    source_effect = {}
    for lvl in QUERY_LEVELS:
        rs = [r for r in rows if r["arm"] in EVIDENCE_ARMS and r["level"] == lvl and r["source"]]
        source_effect[lvl] = {s: {"runs": len(g), "recon": mean([r["recon"] for r in g]),
                                  "failure_rate": mean([1.0 if r["recon"] <= FAIL_THRESHOLD else 0.0 for r in g])}
                              for s in ("not_from_evidence", "same_system_evidence", "transferred_with_justification",
                                        "transferred_without_justification")
                              for g in [[r for r in rs if r["source"] == s]] if g}

    # unit-level: where does the best arm fail, and which units break everything
    units: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        units[(r["paper"], r["level"])].append(r)
    unit_table = []
    for (paper, level), rs in sorted(units.items()):
        arm_means = defaultdict(list)
        for r in rs:
            arm_means[r["arm"]].append(r["recon"])
        means = {a: statistics.fmean(v) for a, v in arm_means.items()}
        unit_table.append({"paper": paper, "level": level, "best": max(means.values()), "worst": min(means.values()),
                           "spread": max(means.values()) - min(means.values()),
                           "best_arm": max(means, key=means.get), "closed_book": means.get("closed_book"),
                           "text_chunks": means.get("text_chunks")})
    all_fail = [u for u in unit_table if u["best"] <= FAIL_THRESHOLD]
    best_arm_counts = Counter(u["best_arm"] for u in unit_table)

    # paper-level summary
    paper_rows = {}
    for paper in sorted({r["paper"] for r in rows}):
        rs = [r for r in rows if r["paper"] == paper]
        counter = Counter(c for r in rs for c in r["categories"])
        total = sum(counter.values())
        paper_rows[paper] = {"recon": mean([r["recon"] for r in rs]),
                             "failure_rate": mean([1.0 if r["recon"] <= FAIL_THRESHOLD else 0.0 for r in rs]),
                             "top_errors": [(c, round(n / max(1, total), 2)) for c, n in counter.most_common(3)]}

    fmt = _read_json(OUT / "format_failure.json") if (OUT / "format_failure.json").exists() else None
    analysis = {
        "fail_threshold": FAIL_THRESHOLD, "runs_analysed": len(rows),
        "extraction_fidelity": fidelity_rows,
        "distortion_examples": {k: v[:6] for k, v in distortion_notes.items()},
        "retrieval_and_use": waterfall, "use_effect_by_level": use_effect,
        "error_mix": error_mix, "failure_error_presence": failure_mix,
        "mechanism_source_effect": source_effect,
        "units_where_all_arms_fail": all_fail, "best_arm_per_unit": dict(best_arm_counts),
        "unit_spread_mean": mean([u["spread"] for u in unit_table]),
        "papers": paper_rows, "format_failure": fmt,
        "coded_errors": sum(len(v["errors"]) for v in codes.values()),
    }
    (OUT / "results").mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / "results" / "analysis.json", analysis)
    (OUT / "results" / "tables.md").write_text(render(analysis))
    return analysis


def _f(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, dict):
        return ", ".join(f"{k}: {_f(v)}" for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return "; ".join(_f(v) for v in value)
    return str(value)


def _grid(title: str, rows: dict[str, dict[str, Any]], cols: list[str]) -> list[str]:
    metrics = list(dict.fromkeys(k for c in cols for k in rows.get(c, {})))
    out = [f"## {title}", "", "| Metric | " + " | ".join(cols) + " |", "|---|" + "---:|" * len(cols)]
    for m in metrics:
        out.append(f"| {m} | " + " | ".join(_f(rows.get(c, {}).get(m)) for c in cols) + " |")
    return out + [""]


def render(a: dict[str, Any]) -> str:
    lines = ["# Failure analysis: extraction-rubric experiment", "",
             f"Runs analysed: {a['runs_analysed']}; coded fatal errors: {a['coded_errors']}; failure = reconstruction "
             f"≤ {a['fail_threshold']}.", ""]
    lines += _grid("1. Extraction fidelity (random sample per rubric)", a["extraction_fidelity"], list(rx.RUBRICS))
    for rubric, notes in a["distortion_examples"].items():
        lines.append(f"- {rubric}: " + " | ".join(n[:200] for n in notes[:4]))
    lines += [""]
    lines += _grid("2–3. Retrieval and use", a["retrieval_and_use"], list(EVIDENCE_ARMS))
    lines += ["## 3b. Effect of citing supportive evidence (evidence arms pooled, within level)", "",
              "| Level | Group | Runs | Reconstruction | Intervention | Mechanism |", "|---|---|---:|---:|---:|---:|"]
    for lvl, groups in a["use_effect_by_level"].items():
        for g, v in groups.items():
            lines.append(f"| {lvl} | {g} | {v['runs']} | {_f(v['recon'])} | {_f(v['intervention'])} | {_f(v['mechanism'])} |")
    lines += [""]
    lines += _grid("4. Error categories (share of each arm's coded fatal errors)", a["error_mix"], list(rx.ARMS))
    lines += _grid("4b. Share of failing runs with at least one error of each category", a["failure_error_presence"], list(rx.ARMS))
    lines += ["## 4c. Mechanism source vs outcome (evidence arms pooled, within level)", "",
              "| Level | Mechanism source | Runs | Reconstruction | Failure rate |", "|---|---|---:|---:|---:|"]
    for lvl, groups in a["mechanism_source_effect"].items():
        for s, v in groups.items():
            lines.append(f"| {lvl} | {s} | {v['runs']} | {_f(v['recon'])} | {_f(v['failure_rate'])} |")
    lines += ["", "## 5. Units and papers", "",
              f"Best arm per unit: {_f(a['best_arm_per_unit'])}. Mean best-minus-worst spread per unit: {_f(a['unit_spread_mean'])}.",
              f"Units where every arm fails: {_f([(u['paper'], u['level'], round(u['best'], 2)) for u in a['units_where_all_arms_fail']])}.",
              "", "| Paper | Reconstruction | Failure rate | Top error categories |", "|---|---:|---:|---|"]
    for p, v in a["papers"].items():
        lines.append(f"| {p} | {_f(v['recon'])} | {_f(v['failure_rate'])} | {_f(v['top_errors'])} |")
    if a["format_failure"]:
        lines += ["", "## 6. Reproduced generation failure (closed_book, PMC11375712 broad)", ""]
        for att in a["format_failure"]["attempts"]:
            lines.append(f"- attempt {att['attempt']}: finish={att['finish_reason']}, chars={att['chars']}, "
                         f"keys={att['top_level_keys']}, has hypothesis string={att['has_hypothesis_string']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("code-errors", "fidelity"):
        p = sub.add_parser(name)
        p.add_argument("--workers", type=int, default=8)
        p.add_argument("--resume", action="store_true")
    sub.add_parser("reproduce")
    sub.add_parser("report")
    args = parser.parse_args()
    if args.command == "code-errors":
        result: Any = code_errors(args.workers, args.resume)
    elif args.command == "fidelity":
        result = fidelity(args.workers, args.resume)
    elif args.command == "reproduce":
        result = {k: v for k, v in reproduce_format_failure().items() if k != "query"}
    else:
        a = report()
        result = {"runs_analysed": a["runs_analysed"], "coded_errors": a["coded_errors"]}
    print(json.dumps(result, indent=2, default=str)[:6000])


if __name__ == "__main__":
    main()
