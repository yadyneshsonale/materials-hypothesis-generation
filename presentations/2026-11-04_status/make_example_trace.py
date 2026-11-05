"""Extract one real run end to end (inputs, intermediate outputs, judge inputs and outputs, and every prompt) for the
2026-11-04 status deck. Offline: network and model calls are blocked, and every rebuilt input is checked against what
the run logged.

    ./.venv/bin/python presentations/2026-11-04_status/make_example_trace.py
writes example_trace.json (complete) and example_trace.md (readable) next to this file.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import rx_experiment  # noqa: E402,F401,I001 - first: it points MATHG_LOOP_ROOT at loop_rx

import json  # noqa: E402
import re  # noqa: E402
from collections import Counter  # noqa: E402
from pathlib import Path  # noqa: E402

import requests  # noqa: E402


def _blocked(*args, **kwargs):
    raise RuntimeError("network or model call attempted: this script must run offline")


requests.get = requests.post = _blocked  # type: ignore[assignment]
requests.Session.request = _blocked  # type: ignore[assignment]

import benchmark_test2 as BT  # noqa: E402
import citegraph as cg  # noqa: E402
import diag_analysis as D  # noqa: E402
import focused_search as FS  # noqa: E402
import hypo_loop as H  # noqa: E402
import llm_client as lc  # noqa: E402
import loop_methods as LM  # noqa: E402
import query_builder_v3 as QB3  # noqa: E402
import query_builder_v3_1 as QB31  # noqa: E402
import refine_loop as RL  # noqa: E402
import rq_judge as RQ  # noqa: E402
import rubric_eval as rx  # noqa: E402
import websearch as ws  # noqa: E402
from temporal_eval_v3 import _blind_candidate  # noqa: E402
from temporal_hypothesis_benchmark import _SCORE_SYSTEM  # noqa: E402

for _name in ("trapi_chat_json", "judge_chat_json", "chat_json"):
    if hasattr(lc, _name):
        setattr(lc, _name, _blocked)

PID, LEVEL, SAMPLE, ARM, BASE = "PMC11643467", "problem_constrained", 1, "rx_r", "rx_base"
E = Path("experiments/high_temperature_hea_qwen35b")
HERE = Path(__file__).resolve().parent
RECON = ("intervention_reconstruction", "condition_agreement", "mechanism_agreement", "outcome_agreement")


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def batches(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def screen_items(rows: list[dict]) -> list[dict]:
    """As focused_search.screen shows papers to the screener."""
    return [{"id": n + 1, "title": re.sub(r"<[^>]+>", "", str(r.get("title", ""))),
             "abstract": str(r.get("abstractText", ""))[:FS.ABSTRACT_CHARS]} for n, r in enumerate(rows)]


def passage_items(records: list) -> list[dict]:
    """As focused_search.grade_passages shows passages to the grader."""
    return [{"id": n + 1, "paper_title": re.sub(r"<[^>]+>", "", str((r.structured or {}).get("title", "")))[:150],
             "section": str(r.kind).split(":", 1)[-1][:60], "text": " ".join(r.text.split())[:FS.PASSAGE_SHOWN]}
            for n, r in enumerate(records)]


def main() -> None:
    rid = H.run_id(PID, LEVEL, ARM, SAMPLE)
    case = H.cases()[PID]
    meta = rx.metadata().get(PID, {})
    manifest = FS.build(PID, LEVEL)  # the cached manifest of the run's focused corpus
    run = read(E / "loop_rx" / ARM / "runs" / f"{rid}.json")

    # Stage 0: how the benchmark case was made (test4 build, loop.md 16.1).
    build_log = read(E / "benchmark_test4" / "build_log" / f"{PID}.json")
    stage0 = {
        "topic_screen_system": BT.TOPIC_SYSTEM,
        "answer_key": {"system": BT.TARGET_SYSTEM,
                       "model": read(E / "benchmark_test4" / "targets" / f"{PID}.json")["extractor"],
                       "input": "the paper's abstract and every section except the Introduction (not reproduced here)",
                       "output": case["hidden_target"]},
        "question": {"gap_system": QB31.GAP_SYSTEM, "gap_output": build_log["gap"],
                     "writer_system": QB3.WRITER_SYSTEM, "writer_model": case.get("query_writer"),
                     "writer_input": {"introduction_without_own_contribution": build_log["source_text"]},
                     "writer_output": build_log["history"][0]["queries"],
                     "checker_system": QB3.CHECKER_SYSTEM, "checker_model": case.get("leakage_checker"),
                     "checks_and_lexical_gate": build_log["history"][0]["checks"], "rounds": len(build_log["history"])},
    }

    # Stages 1-2: plan and searches (the plan as parsed and stored; searches replayed from the query cache).
    h0 = H.Harness(case, LEVEL, 0)  # the build's harness: its seeded generator orders the screening and grading
    flt = ws.CaseFilter(PID)
    _, search_log = FS.run_searches(manifest["plan"], flt)
    assert [(s["query"], s["hit_count"]) for s in search_log] == [(s["query"], s["hit_count"])
                                                                  for s in manifest["searches"]]
    phrases = read(Path(f"{ws.corpus_stem(PID, LEVEL)}.phrases.json"))
    old = read(Path(f"{ws.corpus_stem(PID, LEVEL)}.json"))

    # Stage 3: screening, rebuilt in the build's shuffled order (titles and abstracts from the record cache).
    screened = list(manifest["screen_grades"])  # the BM25 order of the admitted papers, top 120
    core = ws.core_records(screened + list(manifest["expansion_grades"]))
    rows = [core[p] for p in screened]
    h0.rng.shuffle(rows)
    screen_batches = [{"input": {"question": h0.query, "papers": screen_items(batch)},
                       "output_parsed": {"grades": [{"id": n + 1, **manifest["screen_grades"][r["pmcid"]]}
                                                    for n, r in enumerate(batch)]},
                       "pmcids": [r["pmcid"] for r in batch]} for batch in batches(rows, FS.SCREEN_BATCH)]
    exp_rows = [core[p] for p in manifest["expansion_grades"]]
    h0.rng.shuffle(exp_rows)  # one paper: the generator is not advanced, as in the build

    # Stage 4: passage grading, rebuilt; the stored grades are in the grader's shuffled order, which checks the replay.
    terms = FS.plan_terms(manifest["plan"]["groups"])
    records = [r for p in manifest["papers"] for r in FS.paper_records(p)]
    candidates = FS.rank_passages(records, terms, FS.PASSAGES_PER_PAPER)
    h0.rng.shuffle(candidates)
    assert [r.record_id for r in candidates] == list(manifest["passage_grades"]), "passage order replay failed"
    passage_batches = [{"input": {"question": h0.query, "passages": passage_items(batch)},
                        "output_parsed": {"grades": [{"id": n + 1, "grade": manifest["passage_grades"][r.record_id]}
                                                     for n, r in enumerate(batch)]},
                        "record_ids": [r.record_id for r in batch]} for batch in batches(candidates, FS.PASSAGE_BATCH)]

    # Stage 5: the writer's input, rebuilt as refine_loop.m_rx(focused=True, broad=False, loop="none") made it.
    h = H.Harness(case, LEVEL, SAMPLE)
    pack = RL.start_pack(h, True, RL.BUDGET)
    writer_input = {"query": h.query, "knowledge_cutoff": h.cutoff, "analysis_notes": {},
                    "eligible_evidence": RL.items(h, pack)}
    assert len(LM.WRITER_B) + len(json.dumps(writer_input, ensure_ascii=False)) == run["trace"][0]["chars_in"]
    assert sorted(h.seen) == run["seen_ids"]

    # Stage 6: reconstruction judges (GPT-5.6 primary, DeepSeek cross-judge): the same prompt and payload.
    generation, cited = _blind_candidate(run)
    judge_input = {"query": run["query"], "hidden_target": case["hidden_target"], "generated_hypothesis": generation,
                   "cited_evidence": cited}
    gpt = read(E / "loop_rx" / ARM / "judgments" / "gpt56" / f"{rid}.json")
    deep = read(E / "loop_rx" / ARM / "judgments" / "deepseek" / f"{rid}.json")

    # Stage 7: quality judges without the answer key (RQ, three DeepSeek calls; pairwise against the base arm).
    rq_outputs = [read(E / "loop_rq" / "rq" / kind / ARM / "deepseek" / f"{rid}.json")
                  for kind in ("runs", "runs_rep2", "runs_rep3")]
    base = read(E / "loop_rx" / BASE / "runs" / f"{H.run_id(PID, LEVEL, BASE, SAMPLE)}.json")
    gb, eb = _blind_candidate(base)
    pair_inputs = {
        "baseline_first": {"research_question": base["query"], "candidate_A": {"hypothesis": gb, "cited_evidence": eb},
                           "candidate_B": {"hypothesis": generation, "cited_evidence": cited}},
        "new_first": {"research_question": base["query"],
                      "candidate_A": {"hypothesis": generation, "cited_evidence": cited},
                      "candidate_B": {"hypothesis": gb, "cited_evidence": eb}}}
    pair_dir = E / "loop_rx" / "pairwise" / f"{ARM}__vs__{BASE}" / "deepseek"
    pair_outputs = {o: read(pair_dir / f"{PID}__{LEVEL}__s{SAMPLE}__{o}.json") for o in pair_inputs}
    labels = read(E / "loop_rx" / "pack_labels" / "focused" / f"{PID}__{LEVEL}.json")

    trace = {
        "run_id": rid, "arm": ARM, "arm_description": "focused retrieval + the conservative writer (WRITER_B), o3-mini",
        "paper": {"pmcid": PID, "title": re.sub(r"<[^>]+>", "", str(meta.get("title", ""))), "doi": meta.get("doi"),
                  "publication_date": case["publication_date"], "split": case["split"]},
        "user_input": {"level": LEVEL, "question": case["queries"][LEVEL]["text"],
                       "knowledge_cutoff": case["publication_date"],
                       "all_levels": {k: v["text"] for k, v in case["queries"].items()}},
        "stage0_benchmark_case": stage0,
        "stage1_search_plan": {"model": manifest["models"]["search_planner"], "system": FS.PLAN_SYSTEM,
                               "input": {"question": h0.query, "knowledge_cutoff": h0.cutoff},
                               "output_parsed": manifest["plan"]},
        "stage2_search": {"date_filter": ws.filters(case["publication_date"]), "searches": manifest["searches"],
                          "unique_hits": manifest["unique_hits"],
                          "old_corpus_channel": {"model": phrases.get("writer"), "system": cg.KEYWORD_SYSTEM,
                                                 "input": {"question": phrases["question"]},
                                                 "output": {"phrases": phrases["phrases"]},
                                                 "searches": old.get("searches"),
                                                 "papers": manifest["old_corpus_papers"]},
                          "admitted": manifest["admitted"], "channels": manifest["channels"],
                          "rejected": manifest["rejected"]},
        "stage3_screening": {"model": manifest["models"]["screener"], "system": FS.SCREEN_SYSTEM,
                             "batches": screen_batches,
                             "expansion": {"input": {"question": h0.query, "papers": screen_items(exp_rows)},
                                           "output_parsed": manifest["expansion_grades"]},
                             "selected_papers": manifest["papers"]},
        "stage4_passages": {"model": manifest["models"]["passage_grader"], "system": FS.PASSAGE_SYSTEM,
                            "batches": passage_batches, "pack": manifest["pack"], "pack_chars": manifest["pack_chars"],
                            "lever_labels_of_pack_deepseek": dict(Counter(i["lever_match"] for i in labels["items"]))},
        "stage5_writer": {"model": run["models"]["writer"], "system": LM.WRITER_B, "input": writer_input,
                          "output": run["generation"], "trace": run["trace"], "cited_ids": run["cited_ids"]},
        "stage6_reconstruction_judges": {"system": _SCORE_SYSTEM, "input": judge_input, "gpt56_output": gpt,
                                         "deepseek_output": deep,
                                         "reconstruction": {"gpt56": sum(gpt["scores"][k] for k in RECON) / 4,
                                                            "deepseek": sum(deep["scores"][k] for k in RECON) / 4}},
        "stage7_quality_judges": {
            "rq": {"system": RQ.RQ_SYSTEM, "input": json.loads(RQ.payload(run["query"], run["generation"])),
                   "outputs": rq_outputs, "mean_rq": sum(r["rq"] for r in rq_outputs) / len(rq_outputs)},
            "pairwise": {"system": D.QUALITY_PAIR_SYSTEM, "inputs": pair_inputs, "outputs": pair_outputs,
                         "baseline_generation": base["generation"]}},
        "integrity": {"leakage_counters": run["audit"], "target_free_asserted": run["target_free_asserted"],
                      "evidence_records_seen": len(run["seen_ids"])},
    }
    (HERE / "example_trace.json").write_text(json.dumps(trace, indent=1, ensure_ascii=False) + "\n")
    (HERE / "example_trace.md").write_text(render(trace))
    print(f"wrote example_trace.json and example_trace.md in {HERE}; screening batches {len(screen_batches)}, "
          f"passage batches {len(passage_batches)}, writer input {run['trace'][0]['chars_in']} characters")


def block(obj, lang: str = "json") -> str:
    text = obj if isinstance(obj, str) else json.dumps(obj, indent=1, ensure_ascii=False)
    return f"```{lang}\n{text}\n```\n"


def render(t: dict) -> str:
    s0, s1, s2, s3, s4 = (t["stage0_benchmark_case"], t["stage1_search_plan"], t["stage2_search"],
                          t["stage3_screening"], t["stage4_passages"])
    s5, s6, s7 = t["stage5_writer"], t["stage6_reconstruction_judges"], t["stage7_quality_judges"]
    q = s0["question"]
    L = [f"# One real run, end to end: `{t['run_id']}`", "",
         f"Arm: {t['arm_description']}. Paper (hidden from every query-facing model): **{t['paper']['title']}** "
         f"({t['paper']['pmcid']}, doi {t['paper']['doi']}, published {t['paper']['publication_date']}, split "
         f"{t['paper']['split']}).", "",
         "Everything below is verbatim from the run's records. Inputs that were not stored (the screener's and "
         "grader's batches, the writer's payload) were rebuilt offline and checked against what the run logged. "
         "Made by `make_example_trace.py`; the complete machine-readable version is `example_trace.json`.", "",
         "## 0. The user input and how the benchmark made it", "",
         f"**The question given to the agent** ({t['user_input']['level']}; knowledge cutoff "
         f"{t['user_input']['knowledge_cutoff']}):", "", f"> {t['user_input']['question']}", "",
         "The other two levels of the same question:", ""]
    for level, text in t["user_input"]["all_levels"].items():
        if level != t["user_input"]["level"]:
            L.append(f"- **{level}**: {text}")
    L += ["", "**Paper selection screen** (prompt):", "", block(s0["topic_screen_system"], "text"),
          f"**Answer key** ({s0['answer_key']['model']}; input: {s0['answer_key']['input']}). Prompt:", "",
          block(s0["answer_key"]["system"], "text"), "Output (the hidden target the judges compare against):", "",
          block(s0["answer_key"]["output"]), "**Gap type** (prompt, output):", "", block(q["gap_system"], "text"),
          block(q["gap_output"]), f"**Question writer** ({q['writer_model']}). Prompt:", "",
          block(q["writer_system"], "text"), "Input (the paper's introduction with its own contribution removed):", "",
          block(q["writer_input"]), "Output:", "", block(q["writer_output"]),
          f"**Leakage checker** ({q['checker_model']}) and lexical gate (answer-word overlap at most 10%). Prompt:", "",
          block(q["checker_system"], "text"), f"Results (round {q['rounds']}):", "", block(q["checks_and_lexical_gate"]),
          f"## 1. Search plan ({s1['model']})", "", "Prompt:", "", block(s1["system"], "text"), "Input:", "",
          block(s1["input"]), "Output (as parsed and stored):", "", block(s1["output_parsed"]),
          "## 2. Searches (Europe PMC: open access, full text, dated before the paper)", "",
          f"Filter added to every query: `{s2['date_filter']}`", "", "| Search (AND of groups) | Hits | Fetched |",
          "|---|---:|---:|"]
    for s in s2["searches"]:
        L.append(f"| {' AND '.join(s['groups'])} | {s['hit_count']} | {s['fetched']} |")
    oc = s2["old_corpus_channel"]
    L += ["", f"Unique hits: {s2['unique_hits']}. The query of the first search:", "",
          block(s2["searches"][0]["query"], "text"),
          f"**Second channel: the experiment-36 web corpus** ({oc['papers']} papers). Its search phrases were written "
          f"by {oc['model']}. Prompt:", "", block(oc["system"], "text"), "Input:", "", block(oc["input"]), "Output:", "",
          block(oc["output"]), "Its searches:", "", block(oc["searches"]),
          f"Admitted after the date, type and held-out checks: {s2['admitted']} papers (channels {s2['channels']}; "
          f"rejected {s2['rejected']}).", "",
          f"## 3. Relevance screening ({s3['model']}), 20 papers per call in a seeded random order", "", "Prompt:", "",
          block(s3["system"], "text"), "Batch 1, input:", "", block(s3["batches"][0]["input"]),
          "Batch 1, output (parsed):", "", block(s3["batches"][0]["output_parsed"]),
          "All batches (title and grade; the full inputs are in example_trace.json):", "",
          "| Batch | Id | Grade | Why | Title |", "|---:|---:|---:|---|---|"]
    for b, batch in enumerate(s3["batches"], 1):
        for paper, grade in zip(batch["input"]["papers"], batch["output_parsed"]["grades"]):
            L.append(f"| {b} | {paper['id']} | {grade['grade']} | {grade['why']} | {paper['title'][:110]} |")
    L += ["", "Citation expansion (papers co-cited by at least two selected papers), screened the same way:", "",
          block(s3["expansion"]), f"**Selected papers** ({len(s3['selected_papers'])}):", "",
          "| Grade | Channel | Date | Title | Why |", "|---:|---|---|---|---|"]
    for p in s3["selected_papers"]:
        title = re.sub(r"<[^>]+>", "", p["title"])[:100]
        L.append(f"| {p['grade']} | {p.get('channel', '')} | {p.get('date', '')} | {title} | {p['why']} |")
    grades = Counter(g["grade"] for b in s4["batches"] for g in b["output_parsed"]["grades"])
    L += ["", f"## 4. Passage grading ({s4['model']}), 20 passages per call in a seeded random order", "", "Prompt:", "",
          block(s4["system"], "text"), "Batch 1, input:", "", block(s4["batches"][0]["input"]),
          "Batch 1, output (parsed):", "", block(s4["batches"][0]["output_parsed"]),
          f"Grades over all {sum(grades.values())} passages: {dict(sorted(grades.items()))}. The pack: "
          f"{len(s4['pack'])} passages, graded 3 and then 2 ({s4['pack_chars']} characters).", "",
          f"Target-aware check after the run (DeepSeek lever labels of the pack, 0-3): "
          f"{s4['lever_labels_of_pack_deepseek']}. No passage carries the paper's actual lever.", "",
          f"## 5. Writer ({s5['model']})", "", "Prompt (WRITER_B with the output schema):", "",
          block(s5["system"], "text"), f"Input ({s5['trace'][0]['chars_in']} characters with the prompt):", "",
          block(s5["input"]), "Output:", "", block(s5["output"]),
          "## 6. Reconstruction judges (GPT-5.6 primary, DeepSeek-V4-Pro cross-judge)", "", "Prompt (both judges):", "",
          block(s6["system"], "text"),
          "Input (evidence IDs replaced by neutral labels; only the judge sees the answer key):", "",
          block(s6["input"]), "GPT-5.6 output:", "", block(s6["gpt56_output"]), "DeepSeek output:", "",
          block(s6["deepseek_output"]),
          f"Reconstruction = mean of intervention, conditions, mechanism and outcome: GPT-5.6 "
          f"{s6['reconstruction']['gpt56']:.2f}, DeepSeek {s6['reconstruction']['deepseek']:.2f}.", "",
          "## 7. Quality judges without the answer key", "", "**Research quality (RQ)**, three DeepSeek calls. Prompt:",
          "", block(s7["rq"]["system"], "text"), "Input:", "", block(s7["rq"]["input"]), "Outputs:", "",
          block(s7["rq"]["outputs"]),
          f"RQ = mean of the three scales minus 1, averaged over the calls: {s7['rq']['mean_rq']:.2f}.", "",
          "**Pairwise quality** against the base arm (the old web corpus), DeepSeek, both orders. Prompt:", "",
          block(s7["pairwise"]["system"], "text"), "Input, base shown first:", "",
          block(s7["pairwise"]["inputs"]["baseline_first"]), "Outputs:", "", block(s7["pairwise"]["outputs"]),
          "Both orders must agree for a win; here each order picked candidate A, so the pair counts as a tie.", "",
          "## Integrity", "", block(t["integrity"])]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
