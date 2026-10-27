"""Experiment 36 (loop.md 17.1-17.2): does web search help the baselines? The pre-registered analysis.

Harness (loop/ = fixed corpus, loop_web/ = web search):
- W1 (primary): each baseline with web search vs the same baseline without evidence, on every paper both have
  (all 45 = all36 + test4 where available). GPT-5.6 primary, DeepSeek alongside; Holm across the five pairs.
  Decision: web search helps a baseline if the GPT-5.6 CI excludes zero and DeepSeek agrees in direction.
- W2: each web configuration vs its fixed-corpus version, on the papers both cover; Holm across all.
- W3: the web leaderboard, agent tool use, and rank agreement with the fixed-corpus results.
Suite (rerun_v3/ = experiment 21, rerun_web/ = web search; 12 papers, v3 questions):
- W4: web arms vs closed-book, and vs the same arm in experiment 21; Holm within each family.
Leakage:
- W5: every run's leakage counters; every evidence record's dates re-verified; and the evidence-leak test (the share
  of the true case's answer words in the evidence a run saw, minus the share of other cases' answer words), web
  runs against the same configurations on the fixed corpus (which cannot leak by construction).

Outputs: loop_web/analysis_web.json and analysis_web.md; rerun_web/comparison/analysis.json and tables.md.
"""

from __future__ import annotations

import os

os.environ.setdefault("MATHG_CASES_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments",
                                                      "high_temperature_hea_qwen35b", "benchmark_v3_1", "cases"))

import json  # noqa: E402
import statistics  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any, Callable  # noqa: E402

import citegraph as cg  # noqa: E402
import compare_rerun as CR  # noqa: E402
import v4_all_analysis as V  # noqa: E402
import v4_scimon_analysis as A  # noqa: E402
import websearch as ws  # noqa: E402
from hypothesis_evidence_v2 import atomic_json  # noqa: E402

E = A.E
FIXED, WEB = E / "loop", E / "loop_web"
SUITE_FIXED, SUITE_WEB = E / "rerun_v3", E / "rerun_web"
LEVELS = A.V31_LEVELS
JUDGES = ("gpt", "deep")
LEAK_COUNTERS = ("temporal_violations", "test_paper_leaks", "family_leaks", "target_doi_or_title_leaks",
                 "invalid_citations", "unknown_record_ids")
W1_PAIRS = (("web_text_chunks", "closed_book"), ("web_agent", "closed_book"),
            ("web_agent_o3mini", "closed_book_o3mini"), ("web_text_chunks_b_o3mini", "writer_only_b_o3mini"),
            ("web_agent_b_o3mini", "writer_only_b_o3mini"))
BASELINES = ("closed_book", "closed_book_o3mini", "writer_only_b_o3mini")
AGENTS = ("web_agent", "web_agent_o3mini", "web_agent_b_o3mini")
SUITE_CLOSED = "exp14_rubrics:closed_book"
COPIED_ARMS = {"exp7_eval_v3:closed_book", "exp14_rubrics:closed_book", "exp16_improvements:closed_book_fixed"}
ANSWER_FIELDS = ("intervention", "structural_mediator", "mechanism", "predicted_outcome")


def web_configs() -> list[str]:
    os.environ.setdefault("MATHG_LOOP_ROOT", str(WEB))
    import loop_methods as LM
    return list(LM.WEB_CONFIGS)


# ---------------------------------------------------------------- scores

def runs(root: Path, method: str) -> list[dict[str, Any]]:
    return [json.loads(p.read_text()) for p in sorted((root / method / "runs").glob("PMC*.json"))]


def load(root: Path, method: str, judge: str, metric: Callable[[dict[str, int]], float] = A.recon
         ) -> dict[str, dict[str, list[float]]]:
    """{paper: {level: [score per sample]}} for successful, judged runs on v3.1-procedure questions (all splits)."""
    folder = "gpt56" if judge == "gpt" else "deepseek"
    out: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for run in runs(root, method):
        if run.get("status") != "ok" or run["query_level"] not in LEVELS:
            continue
        if run.get("benchmark", "v3.1") not in ("v3.1", "test2", "test3", "test4"):
            continue
        judgment = root / method / "judgments" / folder / f"{run['run_id']}.json"
        if judgment.exists():
            out[run["paper_id"]][run["query_level"]].append(metric(json.loads(judgment.read_text())["scores"]))
    return out


def per_paper(root: Path, method: str, judge: str) -> dict[str, float]:
    return A.per_paper(load(root, method, judge))


def w1() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for judge in JUDGES:
        items = []
        for web_method, base in W1_PAIRS:
            items.append({"config": web_method, "vs": base,
                          **A.paired(per_paper(WEB, web_method, judge), per_paper(FIXED, base, judge))})
        out[judge] = V.holm_family(items)
    decision = {}
    for g, d in zip(out["gpt"], out["deep"]):
        if not g.get("papers"):
            decision[g["config"]] = "no data"
        elif g["ci95"][0] > 0 and d.get("diff", 0) > 0:
            decision[g["config"]] = "helps"
        elif g["ci95"][1] < 0 and d.get("diff", 0) < 0:
            decision[g["config"]] = "hurts"
        else:
            decision[g["config"]] = "no detectable effect"
    papers36 = {p["paper_id"] for p in json.loads((E / "websearch" / "heldout.json").read_text()).values()
                if p["split"] != "test4"}
    sensitivity = {judge: V.holm_family([{"config": w, "vs": b, **A.paired(per_paper(WEB, w, judge),
                                                                           per_paper(FIXED, b, judge), papers36)}
                                         for w, b in W1_PAIRS]) for judge in JUDGES}
    return {"pairs": out, "decision": decision, "all36_only": sensitivity}


def w2(configs: list[str]) -> dict[str, Any]:
    return {judge: V.holm_family([{"config": f"web_{c}", "vs": c, **A.paired(per_paper(WEB, f"web_{c}", judge),
                                                                             per_paper(FIXED, c, judge))}
                                  for c in configs]) for judge in JUDGES}


def agent_use(method: str) -> dict[str, Any]:
    rows = [r for r in runs(WEB, method) if r.get("status") == "ok"]
    notes = [r["notes"].get("web_agent", {}) for r in rows]
    searches = [sum(1 for e in n.get("log", []) if e.get("tool") == "web_search") for n in notes]
    refs = [sum(1 for e in n.get("log", []) if e.get("tool") == "references") for n in notes]
    pages = [len(n.get("pages", [])) for n in notes]
    papers_read = [len({p.split("::")[0] for p in n.get("pages", [])}) for n in notes]
    return {"runs": len(rows), "tool_calls": A_mean([n.get("tool_calls", 0) for n in notes]),
            "searches": A_mean(searches), "reference_lookups": A_mean(refs), "pages_read": A_mean(pages),
            "papers_read": A_mean(papers_read), "runs_reading_nothing": sum(p == 0 for p in pages),
            "cited_records": A_mean([len(r["cited_ids"]) for r in rows])}


def A_mean(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 3) if values else None


def w3(configs: list[str]) -> dict[str, Any]:
    methods = [f"web_{c}" for c in configs] + list(AGENTS)
    board = {}
    for m in methods:
        rs = runs(WEB, m)
        board[m] = {"runs": len(rs), "failed": sum(r.get("status") != "ok" for r in rs),
                    **{judge: A_mean(list(per_paper(WEB, m, judge).values())) for judge in JUDGES},
                    "papers": len(per_paper(WEB, m, "gpt"))}
    for b in BASELINES:
        board[f"{b} (fixed, no evidence)"] = {"runs": len(runs(FIXED, b)), "failed": 0,
                                              **{judge: A_mean(list(per_paper(FIXED, b, judge).values()))
                                                 for judge in JUDGES}, "papers": len(per_paper(FIXED, b, "gpt"))}
    agreement = {}
    for judge in JUDGES:
        web_means, fixed_means = [], []
        for c in configs:
            a, b = per_paper(WEB, f"web_{c}", judge), per_paper(FIXED, c, judge)
            common = set(a) & set(b)
            if common:
                web_means.append(statistics.fmean(a[p] for p in common))
                fixed_means.append(statistics.fmean(b[p] for p in common))
        agreement[judge] = {"configs": len(web_means), "spearman": A.spearman(web_means, fixed_means)}
    return {"leaderboard": board, "rank_agreement_web_vs_fixed": agreement,
            "agent_tool_use": {m: agent_use(m) for m in AGENTS}}


# ---------------------------------------------------------------- suite

def suite_scores(root: Path) -> dict[str, dict[str, dict[str, float]]]:
    raw = CR.load(root)
    for key, values in V.suite_extra_deep(root).items():
        raw["deep"].setdefault(key, values)
    return {judge: V.per_paper_arm(raw[judge]) for judge in JUDGES}


def suite_tool_use() -> dict[str, Any]:
    out = {}
    for sub, setting in (("eval_v3", "tool_agent"), ("eval_v4_matkg", "tool_agent_kg")):
        rows = [json.loads(p.read_text()) for p in sorted((SUITE_WEB / sub / "runs").glob(f"PMC*__{setting}.json"))]
        rows = [r for r in rows if r.get("status") == "ok"]
        out[setting] = {"runs": len(rows), "tool_calls": A_mean([r["tool_calls"] for r in rows]),
                        "runs_with_no_tool_call": sum(1 for r in rows if r["tool_calls"] == 0),
                        "runs_shown_live_web_papers": sum(1 for r in rows if any(a.endswith("::paper")
                                                                                 for a in r["accessed_record_ids"])),
                        "runs_reading_a_live_web_paper": sum(1 for r in rows if any(
                            t.get("tool") == "read_record" and str((t.get("args") or {}).get("record_id", ""))
                            .endswith("::paper") for t in r["tool_trace"] if isinstance(t.get("args"), dict))),
                        "live_web_papers_cited": sum(1 for r in rows for c in r["cited_evidence_ids"]
                                                     if c.endswith("::paper"))}
    return out


def w4() -> dict[str, Any]:
    web, fixed = suite_scores(SUITE_WEB), suite_scores(SUITE_FIXED)
    arms = sorted(a for a in web["gpt"] if a not in COPIED_ARMS)
    out: dict[str, Any] = {"arms": arms, "copied_baselines": sorted(COPIED_ARMS)}
    out["vs_closed_book"] = {judge: V.holm_family([{"config": a, "vs": SUITE_CLOSED,
                                                    **A.paired(web[judge][a], web[judge].get(SUITE_CLOSED, {}))}
                                                   for a in arms if web[judge].get(a)]) for judge in JUDGES}
    out["vs_experiment_21"] = {judge: V.holm_family([{"config": a, "vs": f"{a} (experiment 21)",
                                                      **A.paired(web[judge][a], fixed[judge].get(a, {}))}
                                                     for a in arms if web[judge].get(a) and fixed[judge].get(a)])
                               for judge in JUDGES}
    out["leaderboard"] = {a: {f"{label}_{judge}": (round(statistics.fmean(d[judge][a].values()), 3)
                                                   if d[judge].get(a) else None)
                              for label, d in (("web", web), ("experiment21", fixed)) for judge in JUDGES}
                          for a in sorted(set(arms) | COPIED_ARMS)}
    out["beats_closed_book"] = {judge: [i["config"] for i in out["vs_closed_book"][judge] if V.significant(i) == 1]
                                for judge in JUDGES}
    out["tool_use"] = suite_tool_use()
    graphs = [json.loads(p.read_text())["stats"] for p in sorted((SUITE_WEB / "citegraph" / "cases").glob("PMC*/graph.json"))]
    out["web_graphs"] = {k: A_mean([g[k] for g in graphs]) for k in ("nodes", "full_text_nodes", "edges", "statements",
                                                                     "nodes_with_2plus_citers")} if graphs else {}
    return out


# ---------------------------------------------------------------- W5 leakage

def counters(root: Path, pattern: str = "*/runs/PMC*.json") -> dict[str, Any]:
    totals: Counter[str] = Counter()
    nonzero, checked = [], 0
    for path in sorted(root.glob(pattern)):
        run = json.loads(path.read_text())
        checked += 1
        audit = run.get("audit") or {}
        bad = {k: audit.get(k, 0) for k in LEAK_COUNTERS if int(audit.get(k, 0) or 0)}
        totals.update(bad)
        if bad:
            nonzero.append({"run": str(path.relative_to(E)), **bad})
    return {"runs_checked": checked, "nonzero_runs": len(nonzero), "totals": dict(totals), "examples": nonzero[:10]}


class Evidence:
    """Text and dates of any record a run saw: web records rebuilt from the corpora and caches, fixed-corpus records
    from the experiment-21 pools."""

    def __init__(self) -> None:
        self.papers: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.fixed: dict[str, dict[str, Any]] = {}

    def _paper(self, pmcid: str) -> dict[str, Any]:
        if pmcid not in self.papers:
            entry = ws.entry_for(pmcid)
            parsed = ws.load_parsed(pmcid)
            records = {r.record_id: r for r in ws.passages(entry, parsed)}
            card = ws.card(entry, parsed)
            records[card.record_id] = card
            self.papers[pmcid] = {"entry": entry, "parsed": parsed, "records": records}
            while len(self.papers) > 800:
                self.papers.popitem(last=False)
        return self.papers[pmcid]

    def web(self, record_id: str) -> Any:
        pmcid = record_id.split("::")[0]
        paper = self._paper(pmcid)
        if record_id in paper["records"]:
            return paper["records"][record_id]
        record = ws.resolve(record_id)
        if record is not None:
            paper["records"][record_id] = record
        return record

    def fixed_record(self, case: dict[str, Any], record_id: str) -> Any:
        if case["paper_id"] not in self.fixed:
            import hypo_loop
            import rubric_eval as rx
            hypo_loop.cases()  # registers metadata rows for the later held-out sets (test2-test4)
            lookup = {}
            for representation in ("text_chunks", "card"):
                lookup.update({r.record_id: r for r in rx.case_pool(case, representation)[1]})
            self.fixed[case["paper_id"]] = lookup
        return self.fixed[case["paper_id"]].get(record_id)


def answer_words() -> tuple[dict[str, set[str]], set[str]]:
    cases = ws.held_out_cases()

    def stems(text: str) -> set[str]:
        return {cg._stem(t) for t in cg.content_terms(text) if len(t) > 2}

    raw = {cid: stems(" ".join(str(c["hidden_target"].get(k, "")) for k in ANSWER_FIELDS)) for cid, c in cases.items()}
    frequency = Counter(w for words in raw.values() for w in words)
    common = {w for w, n in frequency.items() if n >= 0.25 * len(raw)}
    out = {}
    for cid, case in cases.items():
        question = stems(" ".join(q["text"] for q in case["queries"].values()))
        out[cid] = raw[cid] - question - common
    return out, common


def stems_of(text: str) -> set[str]:
    return {cg._stem(t) for t in cg.content_terms(text) if len(t) > 2}


def version_check() -> dict[str, Any]:
    """For every corpus paper, the share of its case paper's 12-word passages (non-introduction text) that it contains.
    The build rejects 5% or more (rule f); this reports the actual distribution."""
    shares: list[tuple[float, str]] = []
    cache: dict[str, set[int]] = {}
    for manifest in ws.manifests():
        case_shingles = ws.CaseFilter(manifest["case"]).case_shingles()
        for entry in manifest["seeds"] + manifest["expansion"]:
            if entry["pmcid"] not in cache:
                cache[entry["pmcid"]] = ws.shingles(str(ws.load_parsed(entry["pmcid"]).get("text", "")))
            share = len(case_shingles & cache[entry["pmcid"]]) / max(1, len(case_shingles))
            shares.append((share, f"{manifest['case']}/{manifest['level']}/{entry['pmcid']}"))
    values = sorted(s for s, _ in shares)
    return {"corpus_papers": len(values), "max_share": round(values[-1], 4) if values else None,
            "p99_share": round(values[int(0.99 * (len(values) - 1))], 4) if values else None,
            "median_share": round(statistics.median(values), 4) if values else None,
            "papers_at_or_above_1pct": sum(v >= 0.01 for v in values), "top": sorted(shares, reverse=True)[:5]}


def w5(configs: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {"counters_harness_web": counters(WEB),
                           "counters_suite_web": counters(SUITE_WEB, "**/runs/PMC*.json"),
                           "version_check": version_check()}
    answers, common = answer_words()
    cases = ws.held_out_cases()
    evidence = Evidence()
    date_violations: list[str] = []
    unresolved = 0
    excess: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    pairs = [(f"web_{c}", c) for c in configs]
    for web_method, fixed_method in pairs:
        for root, method, kind in ((WEB, web_method, "web"), (FIXED, fixed_method, "fixed")):
            for run in runs(root, method):
                if run.get("status") != "ok" or run["query_level"] not in LEVELS or run["paper_id"] not in cases:
                    continue
                if run.get("benchmark", "v3.1") not in ("v3.1", "test2", "test3", "test4"):
                    continue
                case = cases[run["paper_id"]]
                texts = []
                for rid in run["seen_ids"]:
                    record = evidence.web(rid) if kind == "web" else evidence.fixed_record(case, rid)
                    if record is None:
                        unresolved += 1
                        continue
                    texts.append(record.text)
                    if kind == "web":
                        dates = [d for d in (record.structured or {}).get("dates", {}).values() if d]
                        if any(d >= case["publication_date"] for d in dates + [record.publication_date]):
                            date_violations.append(f"{run['run_id']}: {rid}")
                if not texts:
                    continue
                seen = stems_of(" ".join(texts))
                own = len(answers[case["paper_id"]] & seen) / max(1, len(answers[case["paper_id"]]))
                others = [len(words & seen) / max(1, len(words)) for cid, words in answers.items()
                          if cid != case["paper_id"] and words]
                excess[f"{kind}:{fixed_method}"][run["paper_id"]].append(own - statistics.fmean(others))
    out["web_evidence_dates_rechecked"] = {"violations": len(date_violations), "examples": date_violations[:10],
                                           "unresolved_records": unresolved}
    leak = []
    for _, fixed_method in pairs:
        web_by = {p: statistics.fmean(v) for p, v in excess.get(f"web:{fixed_method}", {}).items()}
        fixed_by = {p: statistics.fmean(v) for p, v in excess.get(f"fixed:{fixed_method}", {}).items()}
        if web_by:
            leak.append({"config": f"web_{fixed_method}", "web_excess": A_mean(list(web_by.values())),
                         "fixed_excess": A_mean(list(fixed_by.values())) if fixed_by else None,
                         "web_minus_fixed": {"config": f"web_{fixed_method}", **A.paired(web_by, fixed_by)}})
    V.holm_family([item["web_minus_fixed"] for item in leak if item["web_minus_fixed"].get("papers")])
    out["evidence_leak_test"] = {
        "definition": "per run: share of the true case's answer words in the evidence it saw minus the mean share of "
                      "the other cases' answer words; answer words = stems of the key's intervention, mediator, "
                      "mechanism and outcome, minus the case's question words and words in 25% or more of keys",
        "common_words_removed": len(common), "by_config": leak}
    return out


# ---------------------------------------------------------------- reports

def _f(x: Any) -> str:
    return "-" if x is None else (f"{x:+.2f}" if isinstance(x, float) else str(x))


def _cell(i: dict[str, Any] | None) -> str:
    if not i or not i.get("papers"):
        return "-"
    return f"{i['diff']:+.2f} {V._ci(i)} ({i['papers']} papers, Holm p {i.get('holm_p', i.get('p'))})"


def render_harness(h: dict[str, Any]) -> str:
    lines = ["# Experiment 36: web search for every baseline (harness)", "",
             "## W1: each baseline with web search vs the same baseline without evidence (primary)", "",
             "| web configuration | baseline | GPT-5.6 diff [CI] | DeepSeek diff [CI] | decision |", "|---|---|---|---|---|"]
    for g, d in zip(h["W1"]["pairs"]["gpt"], h["W1"]["pairs"]["deep"]):
        lines.append(f"| {g['config']} | {g['vs']} | {_cell(g)} | {_cell(d)} | {h['W1']['decision'][g['config']]} |")
    lines += ["", "## W2: web corpus vs fixed corpus, same configuration", "",
              "| configuration | GPT-5.6 web − fixed [CI] | DeepSeek web − fixed [CI] |", "|---|---|---|"]
    for g, d in zip(h["W2"]["gpt"], h["W2"]["deep"]):
        lines.append(f"| {g['config']} | {_cell(g)} | {_cell(d)} |")
    lines += ["", "## W3: leaderboard (mean over papers)", "", "| configuration | runs | failed | papers | GPT-5.6 | DeepSeek |",
              "|---|---:|---:|---:|---:|---:|"]
    board = h["W3"]["leaderboard"]
    for m in sorted(board, key=lambda m: -(board[m]["gpt"] or -9)):
        b = board[m]
        lines.append(f"| {m} | {b['runs']} | {b['failed']} | {b['papers']} | {b['gpt']} | {b['deep']} |")
    lines += ["", "Rank agreement web vs fixed: " + json.dumps(h["W3"]["rank_agreement_web_vs_fixed"]), "",
              "Agent tool use: " + json.dumps(h["W3"]["agent_tool_use"]), "",
              "## W5: leakage", "", "Counters: " + json.dumps(h["W5"]["counters_harness_web"]["totals"]) +
              f" over {h['W5']['counters_harness_web']['runs_checked']} runs; suite: " +
              json.dumps(h["W5"]["counters_suite_web"]["totals"]) +
              f" over {h['W5']['counters_suite_web']['runs_checked']} runs.", "",
              "Evidence dates re-checked: " + json.dumps(h["W5"]["web_evidence_dates_rechecked"]), "",
              "Version check (share of a held-out paper's 12-word passages in any corpus paper): " +
              json.dumps({k: v for k, v in h["W5"].get("version_check", {}).items() if k != "top"}), "",
              "| configuration | answer-word excess, web | fixed corpus | web − fixed [CI] |", "|---|---:|---:|---|"]
    for item in h["W5"]["evidence_leak_test"]["by_config"]:
        lines.append(f"| {item['config']} | {item['web_excess']} | {item['fixed_excess']} | "
                     f"{_cell(item.get('web_minus_fixed'))} |")
    return "\n".join(lines) + "\n"


def render_suite(s: dict[str, Any]) -> str:
    gc = {i["config"]: i for i in s["vs_closed_book"]["gpt"]}
    dc = {i["config"]: i for i in s["vs_closed_book"]["deep"]}
    g21 = {i["config"]: i for i in s["vs_experiment_21"]["gpt"]}
    d21 = {i["config"]: i for i in s["vs_experiment_21"]["deep"]}
    lines = ["# Experiment 36: the experiment-21 suite with web search (12 papers, v3 questions)", "",
             "| arm | web GPT | web DeepSeek | exp 21 GPT | exp 21 DeepSeek | vs closed-book GPT | vs closed-book DeepSeek | "
             "web − exp 21 GPT | web − exp 21 DeepSeek |", "|---|---:|---:|---:|---:|---|---|---|---|"]
    for a in sorted(s["leaderboard"], key=lambda a: -(s["leaderboard"][a]["web_gpt"] or -9)):
        b = s["leaderboard"][a]
        lines.append(f"| {a}{' (copied)' if a in s['copied_baselines'] else ''} | {b['web_gpt']} | {b['web_deep']} | "
                     f"{b['experiment21_gpt']} | {b['experiment21_deep']} | {_cell(gc.get(a))} | {_cell(dc.get(a))} | "
                     f"{_cell(g21.get(a))} | {_cell(d21.get(a))} |")
    lines += ["", "Beats closed-book: " + json.dumps(s["beats_closed_book"]), "",
              "Tool use: " + json.dumps(s["tool_use"]), "", "Web citation graphs (mean): " + json.dumps(s["web_graphs"]), ""]
    return "\n".join(lines)


def main() -> None:
    configs = web_configs()
    h = {"W1": w1(), "W2": w2(configs), "W3": w3(configs), "W5": w5(configs)}
    atomic_json(WEB / "analysis_web.json", h)
    (WEB / "analysis_web.md").write_text(render_harness(h))
    s = w4()
    atomic_json(SUITE_WEB / "comparison" / "analysis.json", s)
    (SUITE_WEB / "comparison" / "tables.md").write_text(render_suite(s))
    print(render_harness(h))
    print(render_suite(s))


if __name__ == "__main__":
    main()
