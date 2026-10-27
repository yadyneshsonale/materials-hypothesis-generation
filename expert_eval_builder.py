"""Experiment 30 (loop.md section 13): build the blind expert-evaluation package and its internal key.

Stages (resumable):
  select      20 papers (10 of the original 12, 5 of test2, 5 of test3; seed 20261026), random question order
              Q01-Q20, balanced A/B/C assignment of the three sources -> expert_eval/key.json
  references  the paper's actual study rewritten by GPT-5.6 as a forward-looking proposal in the generators' schema;
              fidelity rule: GPT-5.6 judge intervention score >= 3, else one retry; DeepSeek cross-judge
  render      the expert package (expert_evaluation/: Markdown pages, rating workbook, CSV) and
              expert_eval/judge_scores.json (both judges' scores for all 60 items)
  check       blinding check of the package (no model, method or paper identifiers where they must not be)

The expert package never contains the key. Sources: "o3mini_writer" (writer_only_b_o3mini, the recommended
configuration), "llama_baseline" (closed_book), "reference" (the paper's actual study, rewritten).
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import hypo_loop as H
import llm_client as lc
import loop_methods as LM
import rubric_eval as rx
from hypothesis_evidence_v2 import atomic_json
from stage_metrics import CROSS_JUDGE
from temporal_eval_v3 import _blind_candidate, judge_absolute
from temporal_hypothesis_benchmark import _SCORE_SYSTEM, _read_json, _validate_generation, _validate_score

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "expert_evaluation"
INTERNAL = H.EXPERIMENT_DIR / "expert_eval"
REPO_URL = "https://github.com/yadyneshsonale/materials-hypothesis-generation/blob/main/expert_evaluation"
SEED = 20261026
LEVEL = "problem_constrained"
SAMPLE = 1
PER_SET = (("original12", 10), ("test2", 5), ("test3", 5))
SOURCES = {"o3mini_writer": "writer_only_b_o3mini", "llama_baseline": "closed_book", "reference": None}
WRITER = "gpt-5.6-sol_2026-07-09"
PART1 = PACKAGE / "2_part1_blind_rating"
PART2 = PACKAGE / "3_part2_agreement_rating"
SHEET = PACKAGE / "4_rating_sheet"

REFERENCE_SYSTEM = (
    "You help build a blind expert evaluation. You receive a research question and the summary of the published "
    "study that answered it (starting material, intervention or study, conditions, structural mediator, mechanism, "
    "outcome, baseline, boundary, key measurement and actual result). Rewrite the study as the hypothesis proposal "
    "its authors could have written before doing the work, in exactly the JSON schema below, so that it can be shown "
    "next to other researchers' proposals without standing out. Write a proposal, not a methods or results section: "
    "(1) use the future or conditional tense, and never say or imply that anything was observed, measured or "
    "reported; (2) keep every scientific element of the summary: the material, what is changed or studied, the "
    "conditions, the mediator, the mechanism, and the direction and approximate size of the outcome; do not add "
    "anything that is not in the summary; (3) give only the key parameters a proposal would state (for example the "
    "composition, the main process step and its temperature range, or the main simulation method), rounded, and omit "
    "equipment and procedural details such as sample or die sizes, ball-to-powder ratios, rotation speeds, heating "
    "rates, purities, particle sizes, dwell times and instrument settings; (4) give outcomes as approximate "
    "predictions (rounded values or ranges), not exact values; (5) in 'uncertainty' give one realistic uncertainty, "
    "in 'falsification_experiment' turn the key measurement into a test with a falsification rule, and leave the "
    "evidence ID lists empty; (6) keep the total length similar to other proposals, about 250 to 400 words. "
    "Return JSON:\n" + LM.SCHEMA
)

# Friendly labels shown to the expert, in display order.
HYPOTHESIS_LABELS = (
    ("hypothesis", "Main hypothesis"),
    ("material_initial_state", "Starting material"),
    ("intervention", "What is changed or studied"),
    ("conditions", "Conditions"),
    ("structural_mediator", "Structure through which it acts"),
    ("mechanism", "Mechanism"),
    ("predicted_outcome", "Predicted outcome"),
    ("baseline", "Compared with (baseline)"),
    ("boundary", "Where it should hold (boundary)"),
    ("uncertainty", "Main uncertainty"),
)
KEY_LABELS = (
    ("material_initial_state", "Starting material"),
    ("intervention", "What the paper changed or studied"),
    ("conditions", "Conditions"),
    ("structural_mediator", "Structure through which it acted"),
    ("mechanism", "Mechanism"),
    ("predicted_outcome", "Outcome"),
    ("baseline", "Baseline"),
    ("boundary", "Boundary"),
    ("discriminating_measurement", "Key measurement"),
    ("actual_result", "Actual result"),
)
# Words that must never appear in the expert package outside item content (sources, models, pipeline).
SOURCE_WORDS = re.compile(r"(writer_only|closed_book|o3-?mini|llama|gpt-?\d|deepseek|qwen|reference hypothesis|"
                          r"o3mini_writer|llama_baseline|run_id)", re.IGNORECASE)


# ---------------------------------------------------------------- selection

def set_of(case: dict[str, Any]) -> str:
    """original12 = the dev and test splits. Later held-out sets (test4, experiment 35) are their own set and are
    never drawn for this package, which was frozen in experiment 30."""
    split = case["split"]
    if split in ("test2", "test3", "test4"):
        return split
    return "original12"


def select() -> dict[str, Any]:
    cases = H.cases()
    chosen: list[str] = []
    for name, k in PER_SET:
        ids = sorted(pid for pid, c in cases.items() if set_of(c) == name)
        random.Random(SEED).shuffle(ids)
        chosen += ids[:k]
    random.Random(SEED + 1).shuffle(chosen)
    perms = list(itertools.permutations(SOURCES))
    rng = random.Random(SEED + 2)
    sequence = perms * 3 + rng.sample(perms, len(chosen) - 3 * len(perms))
    rng.shuffle(sequence)
    questions = []
    for i, (pid, perm) in enumerate(zip(chosen, sequence), start=1):
        labels = {}
        for label, source in zip("ABC", perm):
            method = SOURCES[source]
            labels[label] = {"source": source, "method": method,
                             "run_id": f"{pid}__{LEVEL}__{method}__s{SAMPLE}" if method else None}
        questions.append({"qid": f"Q{i:02d}", "paper_id": pid, "set": set_of(cases[pid]),
                          "split": cases[pid]["split"], "level": LEVEL, "sample": SAMPLE, "labels": labels})
    key = {"experiment": 30, "rule": "loop.md section 13.1", "seed": SEED, "level": LEVEL, "sample": SAMPLE,
           "sources": {k: v for k, v in SOURCES.items()}, "questions": questions}
    atomic_json(INTERNAL / "key.json", key)
    return key


# ---------------------------------------------------------------- references

def _pseudo_run(pid: str, query: str, generation: dict[str, Any]) -> dict[str, Any]:
    return {"run_id": f"{pid}__{LEVEL}__reference__s{SAMPLE}", "paper_id": pid, "query_level": LEVEL,
            "query": query, "generation": generation, "cited_evidence": []}


def _deepseek(run: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    generation, evidence = _blind_candidate(run)
    payload = {"query": run["query"], "hidden_target": case["hidden_target"], "generated_hypothesis": generation,
               "cited_evidence": evidence}
    raw = lc.trapi_chat_json(CROSS_JUDGE["deployment"], _SCORE_SYSTEM, json.dumps(payload, ensure_ascii=False),
                             max_tokens=8000, token_field=CROSS_JUDGE["token_field"],
                             temperature=CROSS_JUDGE["temperature"], retries=12)
    score = _validate_score(raw)
    return {"run_id": run["run_id"], "judge": f"trapi:{CROSS_JUDGE['deployment']}", "scores": score["scores"],
            "classification": score.get("classification", "")}


def build_reference(pid: str) -> dict[str, Any]:
    path = INTERNAL / "references" / f"{pid}.json"
    if path.exists():
        return _read_json(path)
    case = H.cases()[pid]
    query = case["queries"][LEVEL]["text"]
    payload = {"research_question": query, "study_summary": case["hidden_target"]}
    attempts = []
    for attempt in (1, 2):
        raw = lc.trapi_chat_json(WRITER, REFERENCE_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=6000,
                                 retries=12)
        generation = H._schema_only(_validate_generation(raw, set()))
        run = _pseudo_run(pid, query, generation)
        judgment = judge_absolute(run, case)
        attempts.append({"attempt": attempt, "generation": generation, "gpt56": judgment})
        if judgment["scores"]["intervention_reconstruction"] >= 3:
            break
    accepted = attempts[-1]
    record = {"paper_id": pid, "writer": f"trapi:{WRITER}", "rule": "intervention >= 3 on the GPT-5.6 judge, else "
              "one retry (loop.md 13.1)", "attempts": len(attempts),
              "fidelity_ok": accepted["gpt56"]["scores"]["intervention_reconstruction"] >= 3,
              "generation": accepted["generation"], "gpt56": accepted["gpt56"],
              "deepseek": _deepseek(_pseudo_run(pid, query, accepted["generation"]), case),
              "rejected": attempts[:-1]}
    atomic_json(path, record)
    return record


def references_stage(workers: int = 4) -> dict[str, Any]:
    key = _read_json(INTERNAL / "key.json")
    with ThreadPoolExecutor(workers) as pool:
        records = list(pool.map(build_reference, [q["paper_id"] for q in key["questions"]]))
    return {"references": len(records), "retried": sum(r["attempts"] > 1 for r in records),
            "fidelity_ok": sum(r["fidelity_ok"] for r in records)}


# ---------------------------------------------------------------- items and judge scores

def items() -> list[dict[str, Any]]:
    """The 60 items in question order, with their generation and both judges' scores (internal only)."""
    key = _read_json(INTERNAL / "key.json")
    out = []
    for q in key["questions"]:
        for label in "ABC":
            entry = q["labels"][label]
            if entry["source"] == "reference":
                ref = _read_json(INTERNAL / "references" / f"{q['paper_id']}.json")
                generation, gpt, deep = ref["generation"], ref["gpt56"], ref["deepseek"]
            else:
                base = H.OUT / entry["method"]
                generation = _read_json(base / "runs" / f"{entry['run_id']}.json")["generation"]
                gpt = _read_json(base / "judgments" / "gpt56" / f"{entry['run_id']}.json")
                deep = _read_json(base / "judgments" / "deepseek" / f"{entry['run_id']}.json")
            out.append({"qid": q["qid"], "label": label, "item": f"{q['qid']}-{label}", "paper_id": q["paper_id"],
                        "set": q["set"], "source": entry["source"], "generation": H._schema_only(generation),
                        "gpt56": {"scores": gpt["scores"], "recon": H.recon(gpt["scores"]), "core": H.core(gpt["scores"])},
                        "deepseek": {"scores": deep["scores"], "recon": H.recon(deep["scores"]),
                                     "core": H.core(deep["scores"])}})
    return out


# ---------------------------------------------------------------- rendering

def _clean(value: Any) -> str:
    text = " ".join(str(value or "").split())
    return text.replace("*", "\\*").replace("<", "&lt;").replace(">", "&gt;") or "—"


def _cell(value: Any) -> str:
    return _clean(value).replace("|", "\\|")


def _falsification(value: Any) -> list[str]:
    """The falsification test as nested bullet lines (design, measurements, falsified if)."""
    if not isinstance(value, dict):
        return [f"- **Test that would falsify it:** {_clean(value)}"]
    lines = ["- **Test that would falsify it:**"]
    if value.get("design"):
        lines.append(f"  - *Design:* {_clean(value['design'])}")
    measurements = value.get("measurements")
    if isinstance(measurements, list) and measurements:
        lines.append("  - *Measurements:* " + "; ".join(
            _clean(m if not isinstance(m, dict) else ", ".join(str(v) for v in m.values())) for m in measurements))
    elif measurements:
        lines.append(f"  - *Measurements:* {_clean(measurements)}")
    if value.get("falsification_rule"):
        lines.append(f"  - *Falsified if:* {_clean(value['falsification_rule'])}")
    return lines if len(lines) > 1 else ["- **Test that would falsify it:** —"]


def render_hypothesis(label: str, generation: dict[str, Any], heading: str = "##") -> list[str]:
    lines = [f"{heading} Hypothesis {label}", ""]
    for field, name in HYPOTHESIS_LABELS:
        lines.append(f"- **{name}:** {_clean(generation.get(field))}")
    lines += _falsification(generation.get("falsification_experiment"))
    return lines + [""]


def _nav(qids: list[str], i: int, part_readme: str) -> str:
    parts = [f"[↩ Instructions for this part]({part_readme})"]
    if i > 0:
        parts.append(f"[← Previous: {qids[i - 1]}]({qids[i - 1]}.md)")
    if i < len(qids) - 1:
        parts.append(f"[Next: {qids[i + 1]} →]({qids[i + 1]}.md)")
    return " · ".join(parts)


def _paper_line(pid: str) -> list[str]:
    meta = rx.metadata()[pid]
    year = str(meta.get("publication_year") or meta.get("earliest_public_date", ""))[:4]
    journal = meta.get("journal") or ""
    lines = [f"**{_clean(meta.get('title'))}**", "", f"{journal}{', ' if journal else ''}{year}", ""]
    links = []
    if meta.get("doi"):
        links.append(f"[Journal page (DOI {meta['doi']})](https://doi.org/{meta['doi']})")
    links.append(f"[Free full text (PubMed Central)](https://pmc.ncbi.nlm.nih.gov/articles/{pid}/)")
    links.append(f"[Free full text (Europe PMC, alternative)](https://europepmc.org/article/PMC/{pid})")
    return lines + [" · ".join(links), ""]


def render_package() -> dict[str, Any]:
    key = _read_json(INTERNAL / "key.json")
    cases = H.cases()
    all_items = items()
    by_q = {q["qid"]: [it for it in all_items if it["qid"] == q["qid"]] for q in key["questions"]}
    qids = [q["qid"] for q in key["questions"]]
    one_page_1 = ["# Part 1 – all 20 questions on one page", "",
                  "This page repeats the 20 separate question pages, for printing or scrolling. Rate in the rating "
                  "sheet as described in [the Part 1 instructions](README.md).", ""]
    one_page_2 = ["# Part 2 – all 20 questions on one page", "",
                  "Only open this page after you have finished Part 1 for every question. It repeats the 20 separate "
                  "Part 2 pages. Rate in the rating sheet as described in [the Part 2 instructions](README.md).", ""]
    for i, q in enumerate(key["questions"]):
        qid, case = q["qid"], cases[q["paper_id"]]
        question = _clean(case["queries"][LEVEL]["text"])
        hyp_lines: list[str] = []
        for it in by_q[qid]:
            hyp_lines += render_hypothesis(it["label"], it["generation"]) + ["---", ""]
        p1 = [f"# {qid} – Part 1 (blind rating)", "", _nav(qids, i, "README.md"), "",
              "> Please do **not** look up which paper this question comes from until you have finished Part 1 for "
              "all questions.", "", "## The research question", "", f"> {question}", "",
              "The three hypotheses below were written for this question. Read all three, then rate each one on its "
              "own merits.", "", "---", ""] + hyp_lines + [
              f"## Now rate {qid} in the rating sheet", "",
              f"1. Tab **Part 1 – hypotheses**, rows **{qid}-A**, **{qid}-B** and **{qid}-C**: plausibility, "
              "testability and usefulness (1–5 each).",
              f"2. Tab **Part 1 – questions**, row **{qid}**: does the question make sense (1–5), and which hypothesis "
              "do you think is closest to what the paper's authors actually did (A, B, C or can't tell).", "",
              _nav(qids, i, "README.md"), ""]
        (PART1 / f"{qid}.md").write_text("\n".join(p1))
        one_page_1 += [f"# {qid}", "", "## The research question", "", f"> {question}", "", "---", ""] + \
            [line.replace("## Hypothesis", "### Hypothesis") for line in hyp_lines]
        target = case["hidden_target"]
        key_rows = ["| | |", "|---|---|"] + [f"| **{name}** | {_cell(target.get(field))} |" for field, name in
                                             KEY_LABELS]
        p2 = [f"# {qid} – Part 2 (agreement with the paper)", "", _nav(qids, i, "README.md"), "",
              "> Only open Part 2 after you have finished **Part 1 for all questions**.", "",
              "## The paper", ""] + _paper_line(q["paper_id"]) + [
              "## The research question (same as in Part 1)", "", f"> {question}", "",
              "## What the paper actually did and found (the answer key)", "",
              "This summary was extracted from the paper by an automated method; please check it against the paper "
              "(the abstract and conclusions are usually enough).", ""] + key_rows + ["",
              "## The three hypotheses (the same as in Part 1)", "", "---", ""] + hyp_lines + [
              f"## Now rate {qid} in the rating sheet", "",
              f"1. Tab **Part 2 – hypotheses**, rows **{qid}-A**, **{qid}-B** and **{qid}-C**: agreement with the "
              "paper on intervention, conditions, mechanism and outcome (0–4 each).",
              f"2. Tab **Part 2 – questions**, row **{qid}**: is the answer key accurate (1–5), and does the question "
              "hint at the answer (no, slightly, strongly).", "", _nav(qids, i, "README.md"), ""]
        (PART2 / f"{qid}.md").write_text("\n".join(p2))
        one_page_2 += [f"# {qid}", "", "## The paper", ""] + _paper_line(q["paper_id"]) + [
            "## The research question", "", f"> {question}", "", "## The answer key", ""] + key_rows + [
            "", "## The three hypotheses", "", "---", ""] + \
            [line.replace("## Hypothesis", "### Hypothesis") for line in hyp_lines]
    (PART1 / "ALL_QUESTIONS_ON_ONE_PAGE.md").write_text("\n".join(one_page_1))
    (PART2 / "ALL_QUESTIONS_ON_ONE_PAGE.md").write_text("\n".join(one_page_2))
    write_sheets(qids)
    scores = {it["item"]: {k: it[k] for k in ("qid", "label", "paper_id", "set", "source", "gpt56", "deepseek")}
              for it in all_items}
    atomic_json(INTERNAL / "judge_scores.json", scores)
    return {"questions": len(qids), "items": len(all_items)}


# ---------------------------------------------------------------- rating sheet

PART1_H = ("Plausibility (1-5)", "Testability (1-5)", "Usefulness (1-5)")
PART1_Q = ("Does the question make sense? (1-5)", "Closest to what the authors did (A/B/C/Can't tell)")
PART2_H = ("Intervention (0-4)", "Conditions (0-4)", "Mechanism (0-4)", "Outcome (0-4)")
PART2_Q = ("Answer key accurate? (1-5)", "Question hints at the answer? (No/Slightly/Strongly)")
SHEETS = {"Part 1 – hypotheses": ("2_part1_blind_rating", True, PART1_H),
          "Part 1 – questions": ("2_part1_blind_rating", False, PART1_Q),
          "Part 2 – hypotheses": ("3_part2_agreement_rating", True, PART2_H),
          "Part 2 – questions": ("3_part2_agreement_rating", False, PART2_Q)}
CHOICES = {"(1-5)": "1,2,3,4,5", "(0-4)": "0,1,2,3,4", "(A/B/C/Can't tell)": "A,B,C,Can't tell",
           "(No/Slightly/Strongly)": "No,Slightly,Strongly"}


def _choices(column: str) -> str:
    return next(v for k, v in CHOICES.items() if column.endswith(k))


def write_sheets(qids: list[str]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    start = wb.active
    start.title = "START HERE"
    bold = Font(bold=True)
    rows = [
        ("Expert evaluation of AI-generated materials hypotheses", ""),
        ("", ""),
        ("Your name or initials", ""),
        ("Your field / expertise", ""),
        ("Date", ""),
        ("", ""),
        ("Steps", ""),
        ("1", "Read expert_evaluation/README.md and 1_read_first/README.md (10 minutes)."),
        ("2", "Part 1 (blind): for Q01, Q02, ... open the question page, then fill the two 'Part 1' tabs."),
        ("3", "Only after Part 1 is finished for all questions: Part 2, filling the two 'Part 2' tabs."),
        ("4", "Save this file as expert_ratings_<your initials>.xlsx and send it back (see 5_returned_ratings)."),
        ("", ""),
        ("Progress", ""),
        ("Part 1 – hypotheses", "=COUNTA('Part 1 – hypotheses'!C2:E61)&\" of 180 ratings\""),
        ("Part 1 – questions", "=COUNTA('Part 1 – questions'!B2:C21)&\" of 40 ratings\""),
        ("Part 2 – hypotheses", "=COUNTA('Part 2 – hypotheses'!C2:F61)&\" of 240 ratings\""),
        ("Part 2 – questions", "=COUNTA('Part 2 – questions'!B2:C21)&\" of 40 ratings\""),
        ("", ""),
        ("Each question name in the other tabs is a link to its page. Choose ratings from the drop-down lists.", ""),
    ]
    for r, (a, b) in enumerate(rows, start=1):
        start.cell(r, 1, a)
        start.cell(r, 2, b)
    for r in (1, 7, 13):
        start.cell(r, 1).font = Font(bold=True, size=13 if r == 1 else 11)
    for r in (3, 4, 5):
        start.cell(r, 2).fill = PatternFill("solid", fgColor="FFF2CC")
    start.column_dimensions["A"].width = 32
    start.column_dimensions["B"].width = 100
    shade = PatternFill("solid", fgColor="EEF3FB")
    entry = PatternFill("solid", fgColor="FFFDE7")
    for title, (folder, per_hypothesis, columns) in SHEETS.items():
        ws = wb.create_sheet(title)
        header = ["Question", "Hypothesis"] if per_hypothesis else ["Question"]
        header += list(columns) + ["Comments (optional)"]
        ws.append(header)
        for cell in ws[1]:
            cell.font = bold
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[1].height = 45
        keys = [(q, label) for q in qids for label in "ABC"] if per_hypothesis else [(q, None) for q in qids]
        label_columns = 2 if per_hypothesis else 1
        for n, (qid, label) in enumerate(keys, start=2):
            ws.cell(n, 1, qid).hyperlink = f"{REPO_URL}/{folder}/{qid}.md"
            ws.cell(n, 1).font = Font(color="0563C1", underline="single")
            if per_hypothesis:
                ws.cell(n, 2, label)
            if qids.index(qid) % 2 == 0:  # alternate shading of the label columns groups each question's rows
                for c in range(1, label_columns + 1):
                    ws.cell(n, c).fill = shade
        first = label_columns + 1
        last_row = len(keys) + 1
        for offset, column in enumerate(columns):
            col = first + offset
            dv = DataValidation(type="list", formula1=f'"{_choices(column)}"', allow_blank=True, showErrorMessage=True,
                                errorTitle="Please use the list", error="Please choose a value from the drop-down list.")
            ws.add_data_validation(dv)
            letter = ws.cell(1, col).column_letter
            dv.add(f"{letter}2:{letter}{last_row}")
            ws.column_dimensions[letter].width = 22
            for n in range(2, last_row + 1):
                ws.cell(n, col).fill = entry  # rating cells are always highlighted: this is where to choose
        ws.column_dimensions["A"].width = 11
        if per_hypothesis:
            ws.column_dimensions["B"].width = 11
        ws.column_dimensions[ws.cell(1, len(header)).column_letter].width = 60
        ws.freeze_panes = "A2"
    SHEET.mkdir(parents=True, exist_ok=True)
    wb.save(SHEET / "expert_ratings.xlsx")
    csv_dir = SHEET / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)
    for title, (_, per_hypothesis, columns) in SHEETS.items():
        name = title.lower().replace(" – ", "_").replace(" ", "_")
        with open(csv_dir / f"{name}.csv", "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            header = ["Question", "Hypothesis"] if per_hypothesis else ["Question"]
            writer.writerow(header + list(columns) + ["Comments (optional)"])
            for qid in qids:
                for label in ("ABC" if per_hypothesis else [None]):
                    writer.writerow(([qid, label] if label else [qid]) + [""] * (len(columns) + 1))


# ---------------------------------------------------------------- blinding check

def check_package() -> dict[str, Any]:
    """Part 1 pages, the workbook and the CSVs must not reveal sources, models or papers; Part 2 pages must not reveal
    sources or models. Returns the problems found (an empty list means the package is blind)."""
    key = _read_json(INTERNAL / "key.json")
    H.cases()  # registers the test2/test3 metadata rows
    meta = rx.metadata()
    problems: list[str] = []
    paper_ids = {q["paper_id"] for q in key["questions"]}
    titles = {meta[p]["title"][:40].lower() for p in paper_ids if meta[p].get("title")}
    dois = {str(meta[p].get("doi", "")).lower() for p in paper_ids if meta[p].get("doi")}
    for path in sorted(PART1.glob("*.md")) + sorted(PART2.glob("*.md")):
        text = path.read_text()
        for m in SOURCE_WORDS.finditer(text):
            problems.append(f"{path.relative_to(ROOT)}: source/model word {m.group(0)!r}")
        if path.parent == PART1:
            low = text.lower()
            problems += [f"{path.relative_to(ROOT)}: paper ID {p}" for p in paper_ids if p.lower() in low]
            problems += [f"{path.relative_to(ROOT)}: title" for t in titles if t in low]
            problems += [f"{path.relative_to(ROOT)}: DOI" for d in dois if d in low]
    from openpyxl import load_workbook
    wb = load_workbook(SHEET / "expert_ratings.xlsx")
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            for value in row:
                text = str(value or "")
                if SOURCE_WORDS.search(text) or any(p.lower() in text.lower() for p in paper_ids):
                    problems.append(f"workbook {ws.title}: {text[:60]!r}")
    return {"problems": problems}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("select", "references", "render", "check", "all"))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    for folder in (PART1, PART2, SHEET):
        folder.mkdir(parents=True, exist_ok=True)
    if args.stage in ("select", "all"):
        key = select()
        print({"questions": len(key["questions"]),
               "sets": {s: sum(q["set"] == s for q in key["questions"]) for s, _ in PER_SET}})
    if args.stage in ("references", "all"):
        print(references_stage(args.workers))
    if args.stage in ("render", "all"):
        print(render_package())
    if args.stage in ("check", "render", "all"):
        result = check_package()
        print("blinding problems:", len(result["problems"]), result["problems"][:10])


if __name__ == "__main__":
    main()
