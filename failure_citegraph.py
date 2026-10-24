"""Failure analysis of the citation-graph variants (experiment 18).

Questions, in pipeline order:
  1. Graph construction: how many references resolve, how many nodes have full text or citer statements, and how
     often a node is corroborated by more than one citer.
  2. Citer-statement fidelity: does each extracted statement say what the citing sentence says about the cited work
     (attributed claim, relation, cited system)? A GPT-5.6 checker reads the sentence and the statement.
  3. Evidence ceiling: does the graph (profiles, or the selected papers' cards) contain what anticipates the target?
     Same oracle procedure as experiment 14 (top 20 records by target text, rated by GPT-5.6), compared with the
     ceilings of raw text and cards of the 50-paper corpus.
  4. Retrieval and use: supportive records in context, cited, and the score in each case; whether cited records were
     paper digests or reference-only nodes (citer statements only).
  5. Reasoning: judge error categories (same coder as experiment 15) and audited mechanism source.
  6. Tool agent behaviour: which tools it used, how many nodes it read, and whether that relates to the score.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import citegraph as cg
import llm_client as lc
import rubric_eval as rx
from failure_analysis import CEILING_SYSTEM, CODER_SYSTEM, ERROR_CATEGORIES, ORACLE_TEXT_CHARS, spearman, \
    target_text, validate_labels
from hypothesis_evidence_v2 import atomic_json
from temporal_eval_v3 import PRIMARY_DIMENSIONS, QUERY_LEVELS
from temporal_hypothesis_benchmark import _read_json, retrieve

OUT = cg.OUT / "failure"
FAIL_THRESHOLD = 1.0
ORACLE_K = rx.ORACLE_K
FIDELITY_SAMPLE = 90
POOLS = ("graph_profiles", "graph_selection")
VERDICTS = ("supported", "distorted", "unsupported")
EXP15_CODES = rx.OUT / "failure" / "error_codes"

STATEMENT_CHECK_SYSTEM = (
    "You check statements that were extracted from citing sentences in materials-science papers. Each item has the "
    "citing sentence (and the sentence before it), the title of the cited work, and the extracted statement: what "
    "the cited work found or did according to the sentence (attributed), the relation (finding, method, supports, "
    "contradicts, extends, compares), and the cited material system. Judge only against the sentences given. "
    "attributed: supported if the sentences say this about the cited work, distorted if related but wrong in a "
    "number, direction, alloy system, condition or scope, or if it attributes to the cited work what the sentences "
    "attribute to another work or to the citing paper, unsupported if the sentences do not say it. relation_correct: "
    "true or false. system: supported, distorted, unsupported, or not_applicable if not stated. Return JSON "
    "{\"items\": [{\"id\": str, \"attributed\": str, \"relation_correct\": bool, \"system\": str, \"note\": str}]}. "
    "Give a short note only when something is wrong."
)


# ---------------------------------------------------------------- stage: error coding

def code_errors(workers: int, resume: bool) -> dict[str, int]:
    out = OUT / "error_codes"
    records = cg.load_records()
    jobs = []
    for (_, _, arm, _), rec in records.items():
        if arm in ("closed_book", "text_chunks", "card") or not rec["gpt"] or not rec["gpt"].get("fatal_errors"):
            continue
        rid = rec["run"]["run_id"]
        if not (resume and (out / f"{rid}.json").exists()):
            jobs.append((rid, (rid, rec["gpt"]["fatal_errors"])))

    def job(rid: str, errors: list[Any]) -> None:
        errors = [str(e) for e in errors]
        raw = lc.judge_chat_json(CODER_SYSTEM, json.dumps(
            {"errors": [{"index": i, "text": t} for i, t in enumerate(errors)]}, ensure_ascii=False), max_tokens=6000)
        labels = validate_labels(raw, len(errors))
        atomic_json(out / f"{rid}.json", {"run_id": rid, "coder": lc.judge_info(),
                                          "errors": [{"text": t, "category": labels[i]} for i, t in enumerate(errors)]})

    return cg.run_jobs("fa_code", jobs, job, workers)


# ---------------------------------------------------------------- stage: statement fidelity

def statement_sample() -> list[dict[str, Any]]:
    rng = random.Random(20261023)
    pool = []
    for pmcid in sorted(cg.full_text_papers()):
        path = cg.PAPERS / pmcid / "contexts.json"
        if not path.exists():
            continue
        parsed = _read_json(cg.PAPERS / pmcid / "parsed.json")
        contexts = cg.usable_contexts(parsed)
        for st in _read_json(path)["statements"]:
            ctx = contexts[int(st["ctx"][1:])]
            title = parsed["ref_works"].get(st["cited"], {}).get("title", "")
            pool.append({"id": f"{pmcid}__{st['ctx']}__{st['rid']}", "pmcid": pmcid, "relation": st["relation"],
                         "previous_sentence": cg.clean_sentence(ctx["previous"]),
                         "citing_sentence": cg.clean_sentence(ctx["sentence"]), "cited_title": title,
                         "statement": {"attributed": st["attributed"], "relation": st["relation"],
                                       "cited_system": st["cited_system"]}})
    rng.shuffle(pool)
    by_relation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in pool:
        by_relation[item["relation"]].append(item)
    picked: list[dict[str, Any]] = []
    quota = max(1, FIDELITY_SAMPLE // max(1, len(by_relation)))
    for items in by_relation.values():
        picked += items[:quota]
    rest = [i for i in pool if i not in picked]
    return picked + rest[:max(0, FIDELITY_SAMPLE - len(picked))]


def fidelity(workers: int, resume: bool) -> dict[str, int]:
    out = OUT / "statement_fidelity"
    sample = statement_sample()
    batches = [sample[i:i + 10] for i in range(0, len(sample), 10)]
    jobs = [(f"batch{i:02d}", (i, b)) for i, b in enumerate(batches)
            if not (resume and (out / f"batch{i:02d}.json").exists())]

    def job(index: int, batch: list[dict[str, Any]]) -> None:
        payload = {"items": [{k: v for k, v in item.items() if k not in ("pmcid", "relation")} for item in batch]}
        raw = lc.judge_chat_json(STATEMENT_CHECK_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=8000)
        found = {str(i.get("id")): i for i in (raw.get("items", []) if isinstance(raw, dict) else [])
                 if isinstance(i, dict)}
        rows = []
        for item in batch:
            verdict = found.get(item["id"], {})
            attributed = str(verdict.get("attributed", "")).lower()
            system = str(verdict.get("system", "")).lower()
            rows.append({"id": item["id"], "relation": item["relation"], "statement": item["statement"],
                         "checked": item["id"] in found,
                         "attributed": attributed if attributed in VERDICTS else "unsupported",
                         "relation_correct": bool(verdict.get("relation_correct")),
                         "system": system if system in VERDICTS + ("not_applicable",) else "unsupported",
                         "note": str(verdict.get("note", ""))[:400]})
        atomic_json(out / f"batch{index:02d}.json", {"checker": lc.judge_info(), "items": rows})

    return cg.run_jobs("fa_fidelity", jobs, job, workers)


# ---------------------------------------------------------------- stage: evidence ceiling

def pool_for(case: dict[str, Any], pool: str) -> list[Any]:
    graph = cg.load_graph(case["paper_id"])
    return cg.profile_pool(graph) if pool == "graph_profiles" else cg.selection_pool(graph)


def ceiling(workers: int, resume: bool) -> dict[str, int]:
    out = OUT / "ceiling"
    jobs = [(f"{pool}__{c['paper_id']}", (c, pool)) for c in rx.cases().values() for pool in POOLS
            if not (resume and (out / pool / f"{c['paper_id']}.json").exists())]

    def job(case: dict[str, Any], pool: str) -> None:
        records = pool_for(case, pool)
        top = retrieve(target_text(case["hidden_target"]), records, limit=ORACLE_K)
        if any(r.publication_date >= case["publication_date"] or r.paper_id == case["paper_id"] for r in top):
            raise ValueError("ceiling retrieval returned an ineligible record")
        labels = {f"R{i + 1}": r for i, r in enumerate(top)}
        payload = {"later_paper_date": case["publication_date"],
                   "later_paper_result": {k: case["hidden_target"].get(k) for k in (
                       "material_initial_state", "intervention", "structural_mediator", "mechanism",
                       "predicted_outcome")},
                   "earlier_records": [{"label": label, "date": r.publication_date, "text": r.text[:ORACLE_TEXT_CHARS]}
                                       for label, r in labels.items()]}
        raw = lc.judge_chat_json(CEILING_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=12000)
        raw = raw if isinstance(raw, dict) else {}
        ratings = {}
        for item in raw.get("records", []) if isinstance(raw.get("records"), list) else []:
            if isinstance(item, dict) and str(item.get("label")) in labels:
                ratings[labels[str(item["label"])].record_id] = {
                    "intervention_support": rx._int02(item.get("intervention_support")),
                    "mechanism_support": rx._int02(item.get("mechanism_support"))}
        atomic_json(out / pool / f"{case['paper_id']}.json", {
            "paper_id": case["paper_id"], "pool": pool, "pool_size": len(records), "coder": lc.judge_info(),
            "records": [{"record_id": r.record_id, "has_digest": "Own digest" in r.text or r.kind == "graph_card",
                         "has_citer_statements": "What citing papers say" in r.text,
                         **ratings.get(r.record_id, {"intervention_support": 0, "mechanism_support": 0})}
                        for r in top],
            "reconstructibility": rx._int02(raw.get("reconstructibility")), "reason": str(raw.get("reason", ""))[:1200]})

    return cg.run_jobs("fa_ceiling", jobs, job, workers)


# ---------------------------------------------------------------- report

def mean(values: list[Any]) -> float | None:
    values = [v for v in values if v is not None]
    return round(statistics.fmean(values), 3) if values else None


def recon(scores: dict[str, int]) -> float:
    return statistics.fmean(scores[d] for d in PRIMARY_DIMENSIONS)


def report() -> dict[str, Any]:
    records = cg.load_records()
    codes = {p.stem: _read_json(p) for d in (EXP15_CODES, OUT / "error_codes") if d.exists()
             for p in sorted(d.glob("*.json"))}
    graph_ceil = {pool: {p.stem: _read_json(p) for p in sorted((OUT / "ceiling" / pool).glob("PMC*.json"))}
                  for pool in POOLS}
    base_ceil = {rep: {p.stem: _read_json(p) for p in sorted((rx.OUT / "ceiling" / rep).glob("PMC*.json"))}
                 for rep in ("text_chunks", "card")}

    def supportive(ceil: dict[str, Any], strong: bool = False) -> set[str]:
        return {r["record_id"] for r in ceil["records"]
                if (r["intervention_support"] == 2 or r["mechanism_support"] == 2 if strong
                    else r["intervention_support"] >= 1 or r["mechanism_support"] >= 1)}

    pool_of = {"graph_selection": "graph_selection", "graph_profiles": "graph_profiles",
               "graph_profiles_systemmatch": "graph_profiles", "corroboration_weighted": "graph_profiles",
               "graph_tool_agent": "graph_profiles", "text_chunks": "text_chunks", "card": "card",
               "card_systemmatch": "card"}

    rows = []
    for (paper, level, arm, sample), rec in records.items():
        if not rec["gpt"]:
            continue
        run = rec["run"]
        source = pool_of.get(arm)
        ceil = (graph_ceil.get(source, {}) if source in POOLS else base_ceil.get(source, {})).get(paper)
        sup = supportive(ceil) if ceil else set()
        strong = supportive(ceil, True) if ceil else set()
        packed, cited = set(run.get("packed_ids", [])), set(run.get("cited_ids", []))
        cited_texts = {c["record_id"]: c["text"] for c in run.get("cited_evidence", [])}
        rows.append({
            "rid": run["run_id"], "arm": arm, "paper": paper, "level": level, "recon": recon(rec["gpt"]["scores"]),
            "scores": rec["gpt"]["scores"], "sup_packed": len(packed & sup), "sup_cited": len(cited & sup),
            "strong_packed": len(packed & strong), "cited": len(cited),
            "cited_reference_only": sum(1 for t in cited_texts.values()
                                        if "Paper node" in t and "Own digest" not in t),
            "cited_with_statements": sum(1 for t in cited_texts.values() if "What citing papers say" in t),
            "source": (rec["audit"] or {}).get("mechanism_source"),
            "categories": [e["category"] for e in codes.get(run["run_id"], {}).get("errors", [])],
            "tool_calls": run.get("tool_calls"), "trace": run.get("trace", []),
        })
    arms = tuple(cg.BASELINES) + cg.VARIANTS
    by_arm = {arm: [r for r in rows if r["arm"] == arm] for arm in arms}

    # 1. graph construction
    graph = cg.graph_statistics()

    # 2. statement fidelity
    checked = [i for p in sorted((OUT / "statement_fidelity").glob("*.json")) for i in _read_json(p)["items"]
               if i["checked"]]
    fidelity_by_relation = {}
    for relation in sorted({i["relation"] for i in checked}) + ["all"]:
        items = [i for i in checked if relation == "all" or i["relation"] == relation]
        fidelity_by_relation[relation] = {
            "n": len(items), "attributed_supported": mean([1.0 if i["attributed"] == "supported" else 0.0 for i in items]),
            "attributed_distorted": mean([1.0 if i["attributed"] == "distorted" else 0.0 for i in items]),
            "attributed_unsupported": mean([1.0 if i["attributed"] == "unsupported" else 0.0 for i in items]),
            "relation_correct": mean([1.0 if i["relation_correct"] else 0.0 for i in items]),
            "system_supported_when_stated": mean([1.0 if i["system"] == "supported" else 0.0 for i in items
                                                  if i["system"] != "not_applicable"])}
    fidelity_notes = [f"{i['relation']}: {i['note']}" for i in checked if i["note"]][:12]

    # 3. evidence ceiling
    ceiling_rows = {}
    for name, per in list(graph_ceil.items()) + [(f"corpus_{k}", v) for k, v in base_ceil.items()]:
        cases = list(per.values())
        ceiling_rows[name] = {
            "cases": len(cases), "reconstructibility": mean([c["reconstructibility"] for c in cases]),
            "cases_reconstructible_2": sum(1 for c in cases if c["reconstructibility"] == 2),
            "supportive_in_top20": mean([len(supportive(c)) for c in cases]),
            "strong_in_top20": mean([len(supportive(c, True)) for c in cases]),
            "supportive_that_are_reference_only": mean([
                sum(1 for r in c["records"] if (r["intervention_support"] or r["mechanism_support"])
                    and not r.get("has_digest", True)) / max(1, len(supportive(c))) for c in cases])
            if name in POOLS else None}
    per_case_ceiling = {pid: {name: per[pid]["reconstructibility"]
                              for name, per in list(graph_ceil.items()) + [(f"corpus_{k}", v)
                                                                          for k, v in base_ceil.items()] if pid in per}
                        for pid in sorted(rx.cases())}

    # 4. retrieval and use waterfall
    def stage(r: dict[str, Any]) -> str:
        if r["sup_packed"] == 0:
            return "no_supportive_in_context"
        return "supportive_cited" if r["sup_cited"] else "supportive_in_context_not_cited"

    waterfall = {}
    for arm, rs in by_arm.items():
        if arm == "closed_book" or not rs:
            continue
        counts = Counter(stage(r) for r in rs)
        waterfall[arm] = {
            "runs": len(rs), "failure_rate": mean([1.0 if r["recon"] <= FAIL_THRESHOLD else 0.0 for r in rs]),
            "runs_by_stage": dict(counts),
            "recon_by_stage": {k: mean([r["recon"] for r in rs if stage(r) == k]) for k in counts},
            "mean_supportive_packed": mean([r["sup_packed"] for r in rs]),
            "share_cited_supportive": round(sum(r["sup_cited"] for r in rs) / max(1, sum(r["cited"] for r in rs)), 3),
            "cited_reference_only_share": round(sum(r["cited_reference_only"] for r in rs)
                                                / max(1, sum(r["cited"] for r in rs)), 3)
            if arm in cg.VARIANTS else None,
            "cited_with_citer_statements_share": round(sum(r["cited_with_statements"] for r in rs)
                                                       / max(1, sum(r["cited"] for r in rs)), 3)
            if arm in cg.VARIANTS else None}
    statement_use = {}
    for arm in ("graph_profiles", "graph_profiles_systemmatch", "corroboration_weighted", "graph_tool_agent"):
        rs = by_arm.get(arm, [])
        with_s = [r for r in rs if r["cited_with_statements"] > 0]
        without = [r for r in rs if r["cited"] and r["cited_with_statements"] == 0]
        statement_use[arm] = {"cites_node_with_statements": {"runs": len(with_s), "recon": mean([r["recon"] for r in with_s])},
                              "cites_only_nodes_without_statements": {"runs": len(without),
                                                                      "recon": mean([r["recon"] for r in without])},
                              "cites_nothing": {"runs": sum(1 for r in rs if not r["cited"]),
                                                "recon": mean([r["recon"] for r in rs if not r["cited"]])}}

    # 5. reasoning
    error_mix, failure_mix, source_mix = {}, {}, {}
    for arm, rs in by_arm.items():
        counter = Counter(c for r in rs for c in r["categories"])
        total = sum(counter.values())
        error_mix[arm] = {"errors_per_run": round(total / max(1, len(rs)), 2),
                          **{c: round(counter[c] / max(1, total), 3) for c in ERROR_CATEGORIES}}
        fails = [r for r in rs if r["recon"] <= FAIL_THRESHOLD]
        fc = Counter(c for r in fails for c in set(r["categories"]))
        failure_mix[arm] = {"failures": len(fails), **{c: round(fc[c] / max(1, len(fails)), 3)
                                                       for c in ERROR_CATEGORIES}}
        sources = [r for r in rs if r["source"]]
        source_mix[arm] = {s: {"share": round(sum(1 for r in sources if r["source"] == s) / max(1, len(sources)), 3),
                               "recon": mean([r["recon"] for r in sources if r["source"] == s])}
                           for s in ("not_from_evidence", "same_system_evidence", "transferred_with_justification",
                                     "transferred_without_justification")}
    by_level = {arm: {lvl: {"recon": mean([r["recon"] for r in rs if r["level"] == lvl]),
                            "failure_rate": mean([1.0 if r["recon"] <= FAIL_THRESHOLD else 0.0
                                                  for r in rs if r["level"] == lvl])} for lvl in QUERY_LEVELS}
                for arm, rs in by_arm.items()}

    # 6. tool agent
    agent = by_arm.get("graph_tool_agent", [])
    reads = [sum(1 for t in r["trace"] if t["tool"] == "read_node") for r in agent]
    navigation = [sum(1 for t in r["trace"] if t["tool"] in ("who_cites", "references", "path")) for r in agent]
    agent_rows = {"runs": len(agent), "tool_use": dict(Counter(t["tool"] for r in agent for t in r["trace"])),
                  "runs_using_graph_navigation": sum(1 for n in navigation if n),
                  "reads_mean": mean(reads), "budget_exhausted": sum(1 for r in agent if (r["tool_calls"] or 0) >= 12),
                  "spearman_reads_vs_recon": round(spearman(reads, [r["recon"] for r in agent]), 3)
                  if len(agent) > 2 else None,
                  "recon_with_navigation": mean([r["recon"] for r, n in zip(agent, navigation) if n]),
                  "recon_without_navigation": mean([r["recon"] for r, n in zip(agent, navigation) if not n])}

    # unit-level: best arm and whether graph variants beat card on the same unit
    units: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        units[(r["paper"], r["level"])][r["arm"]].append(r["recon"])
    best_counts: Counter[str] = Counter()
    unit_table = []
    for (paper, level), per in sorted(units.items()):
        means = {a: statistics.fmean(v) for a, v in per.items()}
        top = max(means.values())
        for a, v in means.items():
            if v == top:
                best_counts[a] += 1
        unit_table.append({"paper": paper, "level": level, **{a: round(v, 2) for a, v in means.items()}})

    analysis = {"graph": graph, "statement_fidelity": fidelity_by_relation, "fidelity_notes": fidelity_notes,
                "ceiling": ceiling_rows, "ceiling_per_case": per_case_ceiling, "waterfall": waterfall,
                "statement_use": statement_use, "error_mix": error_mix, "failure_mix": failure_mix,
                "mechanism_source": source_mix, "by_level": by_level, "tool_agent": agent_rows,
                "best_arm_counts": dict(best_counts.most_common()), "units": unit_table}
    OUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / "analysis.json", analysis)
    (OUT / "tables.md").write_text(render(analysis))
    return analysis


def _f(value: Any) -> str:
    return cg._f(value)


def _grid(title: str, rows: dict[str, dict[str, Any]], cols: list[str]) -> list[str]:
    lines = [f"## {title}", "", "| | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for name, row in rows.items():
        lines.append(f"| {name} | " + " | ".join(_f(row.get(c)) if not isinstance(row.get(c), dict)
                                                 else json.dumps(row.get(c)) for c in cols) + " |")
    return lines + [""]


def render(a: dict[str, Any]) -> str:
    lines = ["# Citation-graph failure analysis", ""]
    lines += _grid("Statement fidelity", a["statement_fidelity"],
                   ["n", "attributed_supported", "attributed_distorted", "attributed_unsupported", "relation_correct",
                    "system_supported_when_stated"])
    lines += _grid("Evidence ceiling (top 20 by target text)", a["ceiling"],
                   ["cases", "reconstructibility", "cases_reconstructible_2", "supportive_in_top20", "strong_in_top20",
                    "supportive_that_are_reference_only"])
    lines += _grid("Retrieval and use", a["waterfall"],
                   ["runs", "failure_rate", "mean_supportive_packed", "share_cited_supportive",
                    "cited_reference_only_share", "cited_with_citer_statements_share", "recon_by_stage"])
    lines += _grid("Errors per run and category shares", a["error_mix"], ["errors_per_run", *ERROR_CATEGORIES])
    lines += _grid("Share of failures with each error", a["failure_mix"], ["failures", *ERROR_CATEGORIES])
    lines += ["## Tool agent", "", "```", json.dumps(a["tool_agent"], indent=1), "```", "",
              "## Best arm per unit (ties count for each)", "", "```", json.dumps(a["best_arm_counts"]), "```", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("code", "fidelity", "ceiling", "report"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    resume = not args.no_resume
    stages = {"code": code_errors, "fidelity": fidelity, "ceiling": ceiling}
    result = stages[args.stage](args.workers, resume) if args.stage in stages else report()["best_arm_counts"]
    print(json.dumps(result, indent=1, default=str))


if __name__ == "__main__":
    main()
