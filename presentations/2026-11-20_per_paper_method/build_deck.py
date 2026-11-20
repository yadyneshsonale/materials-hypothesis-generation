"""Build the 2026-11-20 deck: the per-paper generate -> critique -> narrow method (loop.md 28). Same theme and
structure as the 2026-11-10 deck (whose layout helpers and problem slides it reuses): the problem with extract-first
pipelines and the related methods; the method step by step with its prompts and a real run; the evaluation (set,
metrics, prompts) and the results. Reads deck_inputs.json (collect_inputs.py) and ../2026-11-10_on_demand_retrieval/.

    /tmp/pptx_env/bin/python presentations/2026-11-20_per_paper_method/build_deck.py
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("deck_1110", HERE.parent / "2026-11-10_on_demand_retrieval" /
                                               "build_deck.py")
D10 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(D10)  # the simple theme, helpers, problem and related-work slides

from pptx import Presentation  # noqa: E402
from pptx.enum.shapes import MSO_SHAPE  # noqa: E402
from pptx.enum.text import PP_ALIGN  # noqa: E402
from pptx.util import Inches  # noqa: E402

base = D10.base
DI = json.loads((HERE / "deck_inputs.json").read_text())
PR, PROC, PILOT, ALL45, EX = DI["process"], DI["process"], DI["pilot"], DI["all45"], DI["example"]
NOTES = EX["notes"]
OUT = HERE / "per_paper_hypothesis_generation_2026-11-20.pptx"
base.FOOTER = "Hypothesis generation paper by paper · high-temperature HEAs · 20 Nov 2026"
textbox, rect, card, arrow, table, clip, new_slide = (D10.textbox, D10.rect, D10.card, D10.arrow, D10.table,
                                                       D10.clip, D10.new_slide)
prompt_box, strip_tags = D10.prompt_box, D10.strip_tags
NAVY, GRAY, ACCENT, WHITE, LIGHT, BORDER = D10.NAVY, D10.GRAY, D10.ACCENT, D10.WHITE, D10.LIGHT, D10.BORDER
PALE, MONO = D10.PALE_GREEN, D10.MONO
STEPS = 7
OURS, DRAFT, WRITER = "perpaper_dated", "agent_draft_ground_b_o3mini", "writer_only_b_o3mini"
SRC = {"wikipedia": "Wikipedia", "doitpoms": "DoITPoMS", "libretexts": "LibreTexts", "mit_ocw": "MIT OCW"}


def paper(pmcid: str) -> dict:
    return next(p for p in NOTES["papers"] if p["paper"] == pmcid)


def title_of(pmcid: str) -> str:
    for p in NOTES["selected_papers"]:
        if p["pmcid"] == pmcid:
            return strip_tags(p["title"]).rstrip(".")
    return pmcid


SHOWN = "PMC5818523"  # the example paper whose loop needed a revision (2 rounds)
TOP = NOTES["top3"]
MATCH = next(m for m in NOTES["matches"] if m["result"] != 0.5 and TOP[0]["label"] in (m["a"], m["b"]))


def ci(x: dict, digits: int = 2) -> str:
    if not x or not x.get("papers"):
        return "–"
    return f"{x['diff']:+.{digits}f} [{x['ci95'][0]:+.{digits}f}, {x['ci95'][1]:+.{digits}f}]"


def pw(x: dict) -> str:
    return f"{x['diff']:+.2f} ({x['up']} vs {x['down']})" if x and x.get("papers") else "–"


# ---------------------------------------------------------------- part 1

def title_slide(prs) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    textbox(slide, Inches(1.0), Inches(2.0), Inches(11.3), Inches(1.0),
            "Hypothesis generation, paper by paper", size=34, color=NAVY, space=0
            ).text_frame.paragraphs[0].runs[0].font.bold = True
    rect(slide, Inches(1.0), Inches(3.1), Inches(1.4), Inches(0.05), ACCENT)
    textbox(slide, Inches(1.0), Inches(3.35), Inches(11.2), Inches(1.2),
            ["Generate from each retrieved paper, critique against that paper, narrow by tournament",
             "Case study: high-temperature high-entropy alloys"], size=21, color=GRAY, space=4)
    textbox(slide, Inches(1.0), Inches(5.6), Inches(11), Inches(0.9),
            ["The problem with extract-first pipelines · the method, step by step, with its prompts · evaluation and "
             "results", "20 November 2026 · repository materials-hypothesis-generation (loop.md section 28)"],
            size=14, color=GRAY, space=4)
    slide.notes_slide.notes_text_frame.text = (
        "Part 1 (slides 2-3): extract-first pipelines. Part 2 (slides 4-12): the per-paper method (perpaper_dated, "
        "loop.md 28.1-28.5), one slide per step with its prompt, on a real stored run (PMC11643467, "
        "problem-constrained, sample 1; hypotheses/37 on GitHub). Part 3 (slides 13-18): evaluation and results.")


def methods_slide(prs) -> None:
    M = D10.METHODS
    slide = new_slide(prs, "The problem", "Recent methods: what each extracts from papers before generating",
                      notes=M["notes"])
    label = {"yes": "Yes: extraction", "corpus": "Fixed corpus", "no": "No: on demand"}
    rows = [["Method (venue, year)", "Offline pass?", "Preprocessing: what is extracted, by what, over how many papers",
             "Test set"]]
    fills: list = [None]
    for m in M["rows"]:
        rows.append([f"**{m['method']}** ({m['venue']})", label[m["offline"]], m["extract"], m["test"]])
        fills.append(None)
    rows.append(["**Ours: paper by paper** (2026)", "**No: on demand**",
                 f"**Nothing offline.** Per question: retrieve {PROC['papers']:.0f} papers; from each, o3-mini writes "
                 "hypotheses that a critic checks against that paper; a tournament picks the best",
                 "45 HEA papers (2024–2026), 135 questions, leakage-controlled"])
    fills.append(PALE)
    table(slide, Inches(0.55), Inches(1.3), Inches(12.25), rows, [2.85, 1.25, 5.0, 3.15], size=9.5, row_height=0.355,
          fills=fills, header_height=0.32)
    textbox(slide, Inches(0.55), Inches(6.55), Inches(12.25), Inches(0.5), M["footer"], size=10.5, color=GRAY)


# ---------------------------------------------------------------- part 2: the method

def overview_slide(prs) -> None:
    slide = new_slide(prs, "Our approach", "Our method: one idea-generation loop per paper, then a tournament", notes=(
        f"Averages over the 135 question runs on all 45 papers (sample 1, loop.md 28.5). Calls per question: "
        f"{PROC['calls']:.0f} o3-mini calls (generator {PROC['calls_by_role']['generator']:.1f}, revisions "
        f"{PROC['calls_by_role']['generator_revise']:.1f}, critic {PROC['calls_by_role']['critic']:.1f}, tournament "
        f"{PROC['calls_by_role']['narrow']:.1f}), plus the retrieval's plan and screening calls (cached per "
        f"question); {PROC['minutes']:.0f} minutes per question."))
    boxes = [("1 · Question", "+ knowledge cutoff"), ("2 · Retrieve papers", "search + relevance\nscreen"),
             ("3 · Background", "dated textbooks +\nMatKG · no model")]
    x0, y0, bw, bh, gap = Inches(0.55), Inches(1.4), Inches(2.0), Inches(1.15), Inches(0.28)
    for n, (head, sub) in enumerate(boxes):
        x = x0 + n * (bw + gap)
        rect(slide, x, y0, bw, bh, LIGHT if n == 0 else PALE, line=BORDER)
        textbox(slide, x + Inches(0.05), y0 + Inches(0.08), bw - Inches(0.1), bh - Inches(0.1),
                [{"text": f"**{head}**", "size": 12.5, "color": NAVY, "space": 2}] +
                [{"text": s, "size": 10.5, "color": GRAY, "space": 0} for s in sub.split("\n")],
                align=PP_ALIGN.CENTER)
        arrow(slide, x + bw + Inches(0.04), y0 + bh / 2 - Inches(0.09), gap - Inches(0.08), Inches(0.18))
    lx = x0 + 3 * (bw + gap)
    lw = Inches(3.45)
    rect(slide, lx, y0 - Inches(0.12), lw, bh + Inches(0.24), WHITE, line=ACCENT)
    textbox(slide, lx + Inches(0.05), y0 - Inches(0.1), lw - Inches(0.1), Inches(0.3),
            f"**for each of the {PROC['papers']:.0f} papers, in parallel**", size=10, color=ACCENT,
            align=PP_ALIGN.CENTER, space=0)
    for k, (head, sub) in enumerate((("4 · Generate", "3 hypotheses\nfrom the paper"),
                                     ("5 · Critique", "never sees the\nquestion"))):
        bx = lx + Inches(0.12) + k * Inches(1.72)
        rect(slide, bx, y0 + Inches(0.22), Inches(1.5), Inches(0.82), PALE, line=BORDER)
        textbox(slide, bx, y0 + Inches(0.26), Inches(1.5), Inches(0.8),
                [{"text": f"**{head}**", "size": 11.5, "color": NAVY, "space": 1}] +
                [{"text": s, "size": 9.5, "color": GRAY, "space": 0} for s in sub.split("\n")],
                align=PP_ALIGN.CENTER)
    textbox(slide, lx, y0 + Inches(1.05), lw, Inches(0.28), "6 · revise until one is accepted (≤ 20 rounds)",
            size=10, color=ACCENT, align=PP_ALIGN.CENTER, space=0)
    arrow(slide, lx + lw + Inches(0.04), y0 + bh / 2 - Inches(0.09), Inches(0.2), Inches(0.18))
    fx = lx + lw + Inches(0.28)
    rect(slide, fx, y0, Inches(12.8) - fx, bh, PALE, line=BORDER)
    textbox(slide, fx + Inches(0.05), y0 + Inches(0.08), Inches(12.8) - fx - Inches(0.1), bh - Inches(0.1),
            [{"text": "**7 · Narrow**", "size": 12.5, "color": NAVY, "space": 2},
             {"text": "tournament on", "size": 10.5, "color": GRAY, "space": 0},
             {"text": "the question → top 3", "size": 10.5, "color": GRAY, "space": 0}], align=PP_ALIGN.CENTER)
    textbox(slide, Inches(0.55), Inches(2.85), Inches(6.7), Inches(0.35),
            "**What happens to one question** (average over the 135 questions of all 45 papers)", size=13,
            color=NAVY, space=0)
    stages = [(f"{PROC['corpus_papers']:.0f}", "relevant papers found", "searched, dated before the cutoff, screened "
               "for relevance"),
              (f"{PROC['papers']:.0f}", "papers used", "the most relevant, one per first author; each read in full "
               f"(~{PROC['paper_chars'] / 1000:.0f}k characters)"),
              (f"{3 * PROC['papers']:.0f}+", "first hypotheses", f"3 per paper; revised for {100 - 100 * PROC['round1_share']:.0f}% "
               f"of papers (mean {PROC['rounds_mean']:.1f} rounds)"),
              (f"{PROC['pool']:.0f}", "accepted hypotheses", f"from {100 - 100 * PROC['dropped_share']:.0f}% of papers; "
               "the rest dropped after 20 rounds"),
              ("1", "final hypothesis", f"after {PROC['matches']:.0f} tournament matches (+ the ranked top 3)")]
    y = Inches(3.25)
    top = 30.0
    for count, head, body in stages:
        val = float(count.rstrip("+"))
        width = Inches(0.55 + 1.65 * (val / top) ** 0.5)
        rect(slide, Inches(0.55), y, width, Inches(0.55), ACCENT)
        textbox(slide, Inches(0.55), y + Inches(0.08), width, Inches(0.4), f"**{count}**", size=15, color=WHITE,
                align=PP_ALIGN.CENTER, space=0)
        textbox(slide, Inches(2.85), y + Inches(0.02), Inches(4.45), Inches(0.6),
                [{"text": f"**{head}**", "size": 12.5, "space": 0},
                 {"text": body, "size": 10.5, "color": GRAY, "space": 0}], space=0)
        y += Inches(0.7)
    card(slide, Inches(7.45), Inches(2.85), Inches(5.35), Inches(4.0), "Why this design",
         [{"text": "**No offline pass.** Nothing is extracted before a question is asked; papers are read when a "
                   "question needs them.", "bullet": True},
          {"text": "**Every idea starts from one real paper**, but must go beyond it: the critic rejects what the "
                   "paper already did, reported or proposed.", "bullet": True},
          {"text": "**The critic never sees the question**: it judges soundness against the paper and textbook "
                   "knowledge, not relevance. Relevance is judged last, by the tournament.", "bullet": True},
          {"text": "**Leakage-safe**: papers, textbooks and graph facts are all dated before the cutoff.",
           "bullet": True}], body_size=12.5, space=7)


def step_slide(prs, number: int, title: str, what: list, prompt_title: str, prompt: str, example: list, notes: str,
               prompt_size: float = 8.0, left_w: float = 5.0, example_title: str | None = None) -> None:
    slide = new_slide(prs, f"Our method · step {number} of {STEPS}", title, notes=notes)
    textbox(slide, Inches(0.55), Inches(1.35), Inches(left_w), Inches(2.6),
            [{"text": "**What happens**", "size": 13, "color": ACCENT, "space": 4}] +
            [{"text": w, "bullet": True, "size": 12, "space": 4} for w in what], space=4)
    card(slide, Inches(0.55), Inches(4.0), Inches(left_w), Inches(2.9),
         example_title or "Example run (the zirconium paper)", example, body_size=10.5, space=3)
    prompt_box(slide, Inches(0.55 + left_w + 0.2), Inches(1.35), Inches(12.25 - left_w - 0.2), Inches(5.55),
               prompt_title, prompt, size=prompt_size)


def method_steps(prs) -> None:
    run, p = EX["run"], DI["prompts"]
    shown = paper(SHOWN)
    r1, r2 = shown["rounds"][0], shown["rounds"][1]
    note = ("Example: the stored run PMC11643467__problem_constrained__perpaper_dated__s1 (hypotheses/37 on GitHub, "
            "internal_reasoning.json). ")
    step_slide(prs, 1, "The input: a research question and a knowledge cutoff", [
        "The user asks one research question; nothing else is given: no paper, no corpus, no extracted data.",
        "The knowledge cutoff is the date before which every input must be published (here, the hidden paper's "
        "publication date).",
        "In the benchmark the question comes from a held-out paper's introduction, with the paper's own contribution "
        "removed and leakage checked."],
        "Input to the method (JSON)",
        json.dumps({"query": run["query"], "knowledge_cutoff": run["publication_date"]}, indent=1,
                   ensure_ascii=False),
        ["Hidden paper: “The Effect of Zirconium on the Microstructure and Properties of Cast AlCoCrFeNi2.1 Eutectic "
         "High-Entropy Alloy”, 2024-12-01.", "The question never names zirconium, the paper's intervention.",
         "No agent ever sees the hidden paper, its title or its DOI."],
        notes=note, prompt_size=11)
    sel = NOTES["selected_papers"]
    step_slide(prs, 2, "Retrieve the most relevant earlier papers (o3-mini plan, gpt-4o screen)", [
        "o3-mini plans concept groups from the question (material, property, regime, approaches); the searches "
        "combine them in Europe PMC, open access with full text, dated before the cutoff.",
        "Rule checks: two date sources before the cutoff, a research article, not the hidden paper or a relative.",
        "gpt-4o grades each title and abstract 0–3 for relevance; the best 10 (one per first author) are used, each "
        "read in full."],
        "Prompt: relevance screen (gpt-4o, verbatim); before it, a search-plan prompt (o3-mini)", p["SCREEN"],
        [f"Searches found {EX['unique_hits']} papers; {EX['screened']} were screened; {EX['corpus_papers']} kept "
         f"(grade ≥ 2); the top 10 used, e.g.:"] +
        [f"• {clip(strip_tags(s['title']), 80)} ({s['date'][:4]}, grade {s['grade']})" for s in sel[:5]],
        notes=note + "focused_search.py (experiment 44): PLAN_SYSTEM (o3-mini) and SCREEN_SYSTEM (gpt-4o), both "
        "pre-cutoff models; perpaper_loop.select_papers.", prompt_size=10)
    bg = shown["background_items"]
    by = DI["corpus_unique_by_source"]
    step_slide(prs, 3, "Add background knowledge: dated textbooks and MatKG (no model)", [
        f"A teaching corpus of {DI['corpus_unique']:,} passages, every one the version dated on or before 31 Dec 2023 "
        "(Wikipedia revisions; DoITPoMS, LibreTexts and MIT OCW from Internet Archive captures).",
        "For each paper: the 6 passages that best match the question plus the paper's title (word overlap), and up "
        "to 8 MatKG co-occurrence facts from abstracts before the cutoff year.",
        "Passages about high-entropy alloys are removed, so the background carries fundamentals only."],
        "Rule (code, not a prompt)",
        "texts = bm25(question + paper.title, teaching_corpus)\n"
        "        keep 6, at most 2 per document,\n"
        "        only if date < cutoff and no HEA mention\n"
        "facts = matkg(entities in paper.title,\n"
        "              alloy abstracts, years < cutoff year)\n"
        "        keep up to 8, most specific first\n\n"
        "Teaching corpus (unique passages):\n" +
        "\n".join(f"  {SRC[k]:<11} {v:>5,}" for k, v in sorted(by.items(), key=lambda kv: -kv[1])) +
        f"\n  {'total':<11} {DI['corpus_unique']:>5,}   dated 2005 to 2023-12-31",
        [f"For “{clip(title_of(SHOWN), 70)}”:"] +
        [f"• {b['source']} · {clip(b['section'], 30)}: {clip(b['text'], 120)}" for b in bg[:3]],
        notes=note + "materials_texts.py (loop.md 28.4), perpaper_loop.text_records and kg_records.", prompt_size=10.5)
    step_slide(prs, 4, "Generate 3 hypotheses from one paper (o3-mini, 1 call per paper)", [
        "o3-mini receives the question, ONE paper's full text and its background, and writes 3 distinct hypotheses "
        "inspired by that paper.",
        "Each must build on the paper without restating it: carry its finding to the question's material, combine "
        "it with a background principle, or test what it left open.",
        "Each states what it builds on and what is new. The 10 papers run in parallel."],
        "Prompt: generator (o3-mini, verbatim)", p["GENERATOR"],
        [f"Paper: “{clip(title_of(SHOWN), 90)}”. First 3 hypotheses:"] +
        [f"• {clip(h['intervention'], 140)}" for h in r1["hypotheses"]],
        notes=note + "perpaper_loop.GENERATOR_SYSTEM; the same prompt is used for revisions (step 6).",
        prompt_size=7.5, left_w=4.8)
    verdict = lambda rv: " · ".join(f"{c.replace('_', ' ')} {'✓' if rv[c]['pass'] else '✗'}"  # noqa: E731
                                    for c in ("sound", "testable", "beyond_paper"))
    step_slide(prs, 5, "Critique against the paper, without seeing the question (o3-mini)", [
        "The critic receives the paper, the background and the 3 hypotheses, but not the question: it judges "
        "soundness, not relevance.",
        "It first lists what the paper did, reported and proposed, then checks each hypothesis: sound, testable, "
        "and beyond the paper. Accepted only if all three pass.",
        "Every failure comes with a reason, a quote and a concrete fix."],
        "Prompt: critic (o3-mini, high reasoning effort, verbatim)", p["CRITIC"],
        [f"The critic's notes: the paper did “{clip(r1['critic_summary']['paper_did'][1], 120)}”"] +
        [f"• {clip(h['intervention'], 60)}: {verdict(rv)}" for h, rv in zip(r1["hypotheses"], r1["reviews"])] +
        [f"Reason (1st): {clip(r1['reviews'][0]['sound']['reason'], 150)}"],
        notes=note + f"Round 1 of {SHOWN}: none accepted. Over all 135 questions, round-1 pass rates: sound "
        f"{PROC['pass_round1']['sound']:.0%}, beyond the paper {PROC['pass_round1']['beyond_paper']:.0%}, testable "
        f"{PROC['pass_round1']['testable']:.0%}.", prompt_size=8.0, left_w=5.0)
    revise_input = ("Same generator prompt (step 4), with two extra inputs:\n\n"
                    "{\n \"research_question\": ..., \"knowledge_cutoff\": ...,\n \"paper\": [...], "
                    "\"background\": [...],\n \"previous_hypotheses\": [H1, H2, H3],\n \"critique\": [\n  {\"id\": "
                    "\"H1\",\n   \"sound\": {\"pass\": false, \"reason\": ...},\n   \"testable\": {\"pass\": true, "
                    "\"reason\": ...},\n   \"beyond_paper\": {\"pass\": true, \"reason\": ...},\n   \"evidence_quote\": "
                    "..., \"fix\": ...},\n  ...]\n}\n\nThe prompt's revision rule:\n\"If previous hypotheses and a "
                    "critique are supplied, revise: fix every problem the critique names, or replace the hypothesis "
                    "with a better one. Keep answering the research question.\"\n\n"
                    "Loop: stop at the first round with an accepted hypothesis\n(keep every accepted one); after 20 "
                    "rounds, drop the paper.")
    step_slide(prs, 6, "Revise from the critique until a hypothesis is accepted (≤ 20 rounds)", [
        "The generator gets its previous hypotheses and the critique, and fixes or replaces them; the critic checks "
        "the new set.",
        f"Over all questions: {PROC['round1_share']:.0%} of papers succeed in round 1; mean "
        f"{PROC['rounds_mean']:.1f} rounds, at most {PROC['rounds_max']}; {PROC['dropped_share']:.1%} of papers "
        "are dropped.",
        f"Result: about {PROC['pool']:.0f} accepted hypotheses per question, from different papers."],
        "Revision input (JSON shape) and the loop rule", revise_input,
        [f"Round 2 for the same paper, after the critique (✓ = accepted):"] +
        [f"• {'✓' if rv['accepted'] else '✗'} {clip(h['intervention'], 120)}"
         for h, rv in zip(r2["hypotheses"], r2["reviews"])] +
        [f"Critic on the boron idea: “{clip(r2['reviews'][0]['beyond_paper']['reason'], 130)}”"],
        notes=note + "perpaper_loop.per_paper.", prompt_size=9.5)
    tour = NOTES["tournament"]
    first_is_top = MATCH["a"] == TOP[0]["label"]
    other = MATCH["b"] if first_is_top else MATCH["a"]
    other_h = next(c for c in NOTES["pool"] if c["label"] == other)
    step_slide(prs, 7, "Narrow by a tournament on the question (o3-mini, high effort)", [
        f"All accepted hypotheses ({len(NOTES['pool'])} here) meet in pairs; the judge sees the question and both "
        "hypotheses, in both orders; a win needs both orders.",
        f"5 Swiss rounds, then a round robin of the top 5 gives the ranking (about {PROC['matches']:.0f} matches, "
        f"{PROC['calls_by_role']['narrow']:.0f} calls per question).",
        "The output is rank 1, with the ranked top 3."],
        "Prompt: narrowing judge (o3-mini, high reasoning effort, verbatim)", p["NARROW"],
        [f"Match: “{clip(TOP[0]['fields']['intervention'], 80)}” vs “{clip(other_h['fields']['intervention'], 70)}”",
         f"Both orders chose the first: “{clip(MATCH['reasons'][0]['reason'], 150)}”",
         f"Final round robin points: {', '.join(f'{x:g}' for x in tour['final_points'])} (rank 1 tied with rank 2; "
         f"the Swiss-round points break the tie)."],
        notes=note + "perpaper_loop.narrow; ties for rank 1 happen in "
        f"{PROC['tied_share']:.0%} of questions.", prompt_size=12)


def output_slide(prs) -> None:
    g = EX["run"]["generation"]
    slide = new_slide(prs, "Our method · output", "The final hypothesis (rank 1) and the ranked top 3", notes=(
        "hypotheses/37/final_hypothesis.json (problem-constrained). The hidden paper's own answer was adding "
        "zirconium; the method is not scored on matching it."))
    fields = [("Hypothesis", g["hypothesis"]), ("Intervention", g["intervention"]),
              ("Structural mediator", g["structural_mediator"]), ("Mechanism", g["mechanism"]),
              ("Predicted outcome", g["predicted_outcome"]),
              ("Falsification rule", g["falsification_experiment"]["falsification_rule"])]
    card(slide, Inches(0.55), Inches(1.35), Inches(7.4), Inches(5.55),
         f"Rank 1 · source paper: {clip(title_of(TOP[0]['paper']), 40)}",
         [{"text": f"**{k}:** {clip(v, 330 if k == 'Mechanism' else 260)}", "size": 10.5, "space": 5}
          for k, v in fields], body_size=10.5, space=5)
    card(slide, Inches(8.15), Inches(1.35), Inches(4.65), Inches(5.55), "Top 3 (each from a different paper)",
         [{"text": f"**{n}.** {clip(t['fields']['hypothesis'], 170)}", "size": 10.5, "space": 2} for n, t in
          enumerate(TOP, 1)] + [{"text": f"from: {clip(title_of(t['paper']), 60)}", "size": 9, "color": GRAY,
                                 "space": 8} for t in []] +
         [{"text": f"Sources: " + "; ".join(f"{n}. {clip(title_of(t['paper']), 55)}" for n, t in enumerate(TOP, 1)),
           "size": 9.5, "color": GRAY, "space": 6},
          {"text": f"This run: {EX['run']['llm_calls']} calls, {EX['run']['elapsed_seconds'] / 60:.0f} minutes; "
                   "every leakage counter zero.", "size": 9.5, "color": GRAY}], body_size=10.5, space=3)


# ---------------------------------------------------------------- part 3: evaluation and results

def eval_set_slide(prs) -> None:
    slide = new_slide(prs, "Evaluation", "Evaluation set and protocol", notes=(
        "Pilot pre-registered in loop.md 28.1 and repeated on the dated corpus (28.4-28.5). The 45-paper run was not "
        "pre-registered as an evaluation; its scores are exploratory. All 45 papers have been used for development."))
    rows = [["Set", "Papers", "Published"], ["dev", "8", "Jan–Nov 2024"], ["test", "4", "Apr 2025 – Feb 2026"],
            ["test2", "12", "Jul 2025 – Jul 2026"], ["test3", "12", "Jan 2024 – Jun 2025"],
            ["test4", "9", "Nov 2024 – Mar 2026"], ["**Total**", "**45**", "Jan 2024 – Jul 2026"]]
    table(slide, Inches(0.55), Inches(1.4), Inches(5.0), rows, [1.3, 1.1, 2.6], size=12.5, row_height=0.42)
    textbox(slide, Inches(0.55), Inches(4.55), Inches(5.0), Inches(2.3), [
        {"text": "**Pilot (pre-registered):** 8 dev papers × 3 question levels × 2 samples = 48 hypotheses",
         "size": 13, "space": 6},
        {"text": "**All 45 papers (exploratory):** 45 × 3 levels × 1 sample = 135 hypotheses", "size": 13,
         "space": 6},
        {"text": "Compared with two earlier methods on the same questions: the draft-then-read agent and the "
                 "closed-book writer (o3-mini, no retrieval).", "size": 12, "color": GRAY}])
    card(slide, Inches(5.85), Inches(1.4), Inches(6.95), Inches(5.45), "How leakage is prevented", [
        {"text": "**Questions** are written from the paper's introduction with every sentence about the paper's own "
                 "work removed; a checker that sees the answer flags leaking phrases.", "bullet": True},
        {"text": "**Only models trained before the papers** run the method: o3-mini and gpt-4o (cutoffs 2023).",
         "bullet": True},
        {"text": "**Papers dated before the cutoff** by Europe PMC and Crossref; the hidden paper, its DOI, title and "
                 "relatives are blocked from every input.", "bullet": True},
        {"text": "**Background dated too:** every textbook passage is the version from on or before 31 Dec 2023; "
                 "MatKG facts come from years before the cutoff year.", "bullet": True},
        {"text": f"Re-checked after the runs: {PILOT['leakage']['records_rechecked']:,} paper passages and "
                 f"{PILOT['leakage']['background']['text_passages_seen']:,} textbook passages (pilot): 0 leaks.",
         "bullet": True},
        {"text": "**Caveat:** all 45 papers have been used during development; a clean claim needs a fresh set.",
         "bullet": True}], body_size=13, space=7)


def metrics_slide(prs) -> None:
    v = D10.R["controls"]["gaps"]
    slide = new_slide(prs, "Evaluation", "Metrics: how strong is the research proposal?", notes=(
        "RQ: rq_judge.py (loop.md 24.1). Pairwise: noncopy_eval.PAIR_SYSTEM_V2 (loop.md 27.5), the experiment-46 "
        "prompt with criterion 4 replaced by 'goes beyond the earlier work'. Go / no-go rule: loop.md 28.1."))
    card(slide, Inches(0.55), Inches(1.4), Inches(6.1), Inches(2.6), "Research quality, RQ (0–4)", [
        {"text": "RQ = mean(plausibility, testability, usefulness) − 1", "size": 14, "font": MONO, "space": 8},
        {"text": "**Plausibility, testability, usefulness** (1–5): the materials expert's own blind scales, with "
                 "their anchors verbatim.", "bullet": True},
        {"text": "Judged by DeepSeek-V4-Pro from the question and the hypothesis only; mean of 3 calls.",
         "bullet": True}], body_size=12.5, space=4)
    card(slide, Inches(6.85), Inches(1.4), Inches(5.95), Inches(2.6), "Head-to-head preference", [
        {"text": "Our hypothesis vs the other method's, for the same question and sample.", "bullet": True},
        {"text": "Shown in both orders; a win needs both. Net preference per paper, 95% CI over papers.",
         "bullet": True},
        {"text": "Two judges: **DeepSeek** and **o1**. Go rule: both prefer ours to the draft-then-read agent, and "
                 "RQ not lower by more than 0.1.", "bullet": True}], body_size=12, space=4)
    rows = [["Check of the research-quality judge (before use)", "Result", "Pass"],
            ["Good hypotheses vs generic ones (RQ)", f"+{v['rq_positive_minus_generic']:.2f} (≥ 1)", "✓"],
            ["Good hypotheses vs ones written for another question (usefulness)",
             f"+{v['usefulness_positive_minus_random']:.2f} (≥ 1)", "✓"],
            ["Good hypotheses vs ones with a swapped intervention (plausibility)",
             f"+{v['plausibility_positive_minus_intervention_swap']:.2f} (≥ 0.5)", "✓"],
            ["Good hypotheses vs ones with a swapped mechanism (plausibility)",
             f"+{v['plausibility_positive_minus_mechanism_swap']:.2f} (≥ 0.5)", "✓"],
            ["Same 135 hypotheses judged again", "Spearman 0.82 (≥ 0.80)", "✓"]]
    table(slide, Inches(0.55), Inches(4.2), Inches(12.25), rows, [6.4, 4.85, 1.0], size=11.5, row_height=0.4)


def eval_prompts(prs) -> None:
    rq = DI["prompts"]["RQ"]
    cut = rq.index("Rate the hypothesis on three")
    slide = new_slide(prs, "Evaluation · prompts (verbatim)", "Research-quality judge (DeepSeek, 3 calls per hypothesis)",
                      notes="rq_judge.RQ_SYSTEM; input: the question and the hypothesis; no evidence, no answer key.")
    rect(slide, Inches(0.55), Inches(1.35), Inches(12.25), Inches(5.6), LIGHT, line=D10.RGB_LINE)
    textbox(slide, Inches(0.67), Inches(1.43), Inches(12.0), Inches(0.3),
            "The research-quality judge's prompt (one prompt, one judge: DeepSeek), shown in two columns",
            size=11.5, color=ACCENT, space=0).text_frame.paragraphs[0].runs[0].font.bold = True
    for x, part in ((0.67, rq[:cut].rstrip()), (6.8, rq[cut:])):
        textbox(slide, Inches(x), Inches(1.78), Inches(5.9), Inches(5.1),
                [{"text": line or " ", "size": 8.5, "font": MONO, "space": 0} for line in part.split("\n")], space=0)
    line = slide.shapes.add_connector(1, Inches(6.68), Inches(1.8), Inches(6.68), Inches(6.8))
    line.line.color.rgb = D10.RGB_LINE
    slide = new_slide(prs, "Evaluation · prompts (verbatim)", "Head-to-head judge (DeepSeek · o1, both orders)",
                      notes="noncopy_eval.PAIR_SYSTEM_V2, verbatim as it was run.")
    prompt_box(slide, Inches(0.55), Inches(1.35), Inches(7.6), Inches(4.3), "Head-to-head judge prompt",
               DI["prompts"]["PAIR_V2"], size=11)
    card(slide, Inches(8.4), Inches(1.35), Inches(4.4), Inches(4.3), "Input to the judge", [
        {"text": "The research question.", "bullet": True},
        {"text": "Candidate A and candidate B: each hypothesis with the passages it cites (neutral labels).",
         "bullet": True},
        {"text": "Every pair is judged twice, with A and B swapped; a win needs both.", "bullet": True},
        {"text": "No answer key, no method names.", "bullet": True}], body_size=13, space=6)


def results_slides(prs) -> None:
    m = ALL45["means"]
    slide = new_slide(prs, "Results", "Results: higher research quality, preferred over the closed-book writer", notes=(
        "Top: all 45 papers, sample 1 (135 questions), exploratory; baselines judged in earlier sessions (the "
        "writer's RQ drifted by up to +0.05 between sessions). Bottom: paired over papers, net preference with "
        "(papers for vs against). Pilot = the pre-registered 8 dev papers x 2 samples (loop.md 28.5)."))
    rows = [["Method (45 papers, 135 questions)", "RQ", "Plausibility", "Testability", "Usefulness", "Calls"]]
    labels = [(OURS, "**Ours: paper by paper**", f"{PROC['calls']:.0f}"),
              (DRAFT, "Draft-then-read agent", "3"), ("rx_r", "Read on demand, then write", "3")]
    for key, label, calls in labels:
        x = m[key]
        rows.append([label, f"{x['rq']:.2f}", f"{x['plausibility']:.2f}", f"{x['testability']:.2f}",
                     f"{x['usefulness']:.2f}", calls])
    table(slide, Inches(0.55), Inches(1.35), Inches(12.25), rows, [4.6, 1.4, 1.6, 1.6, 1.6, 1.45], size=11.5,
          row_height=0.42, fills=[None, PALE, None, None])
    pc, ac = PILOT["contrasts"], ALL45["vs"]
    rows = [["Ours vs", "Set", "RQ difference", "DeepSeek prefers", "o1 prefers"],
            ["Draft-then-read agent", "pilot (8 papers)", ci(pc["draft"]["rq"]), pw(pc["draft"]["pairwise_v2_deepseek"]),
             pw(pc["draft"]["pairwise_v2_o1"])],
            ["Draft-then-read agent", "all 45 papers", ci(ac["draft"]["rq"]), pw(ac["draft"]["deepseek"]),
             pw(ac["draft"]["o1"])],
            ["Closed-book writer", "pilot (8 papers)", ci(pc["writer"]["rq"]), pw(pc["writer"]["pairwise_v2_deepseek"]),
             pw(pc["writer"]["pairwise_v2_o1"])],
            ["Closed-book writer", "all 45 papers", ci(ac["writer"]["rq"]), pw(ac["writer"]["deepseek"]),
             pw(ac["writer"]["o1"])]]
    table(slide, Inches(0.55), Inches(3.35), Inches(12.25), rows, [3.0, 2.0, 2.45, 2.4, 2.4], size=11.5,
          row_height=0.42)
    textbox(slide, Inches(0.55), Inches(5.65), Inches(12.25), Inches(1.2),
            "RQ on 0–4; the three scales on 1–5. Differences paired by paper with 95% intervals; head-to-head: net "
            "preference, in brackets the papers in which each side is preferred. Pilot = the pre-registered 8 dev "
            "papers × 2 samples; all 45 papers = exploratory (sample 1 for every method, so the agent's RQ is 3.12 here "
            "against 3.16 over both samples).", size=11, color=GRAY)
    x = m[OURS]
    slide = new_slide(prs, "Results", "What the results say", notes=(
        "Pilot decision (loop.md 28.5): go, narrowly (DeepSeek +0.02 over the draft-then-read agent is a tie). Cost: "
        f"{PROC['calls']:.0f} o3-mini calls and {PROC['minutes']:.0f} minutes per question; "
        f"{PROC['calls_by_role']['narrow']:.0f} of the calls are the tournament."))
    base.bar_chart(slide, Inches(0.45), Inches(1.35), Inches(6.3), Inches(3.0), "Our method's three scales (1–5)",
                   ["Usefulness", "Testability", "Plausibility"],
                   [x["usefulness"], x["testability"], x["plausibility"]], [ACCENT, ACCENT, ACCENT],
                   maximum=5.0, cat_size=12)
    w = ac["writer"]
    textbox(slide, Inches(0.55), Inches(4.6), Inches(6.2), Inches(2.3), [
        {"text": "**Preferred over the closed-book writer by both judges** (all 45 papers)", "size": 13.5,
         "space": 4},
        {"text": f"DeepSeek {w['deepseek']['diff']:+.2f}: {w['deepseek']['up']} papers vs {w['deepseek']['down']}",
         "bullet": True, "size": 12.5},
        {"text": f"o1 {w['o1']['diff']:+.2f}: {w['o1']['up']} vs {w['o1']['down']}", "bullet": True, "size": 12.5}],
        space=3)
    d = ac["draft"]
    card(slide, Inches(7.0), Inches(1.4), Inches(5.8), Inches(5.5), "Findings", [
        {"text": f"**Highest research quality of the methods compared** (RQ {x['rq']:.2f} on all 45 papers), mainly from "
                 f"usefulness ({x['usefulness']:.2f} of 5).", "bullet": True},
        {"text": "**Both judges prefer it to the closed-book writer**, on the pilot and on all 45 papers.",
         "bullet": True},
        {"text": f"**Against the draft-then-read agent the judges disagree**: o1 prefers ours "
                 f"({d['o1']['up']} vs {d['o1']['down']} papers), DeepSeek slightly prefers the agent "
                 f"({d['deepseek']['up']} vs {d['deepseek']['down']}). The pilot passed the go rule only narrowly.",
         "bullet": True},
        {"text": "**No extraction corpus**, and every input dated before the cutoff.", "bullet": True},
        {"text": f"**Cost**: about {PROC['calls']:.0f} model calls and {PROC['minutes']:.0f} minutes per question "
                 f"(the agent: 3); {PROC['calls_by_role']['narrow'] / PROC['calls']:.0%} of the calls are the "
                 "tournament.", "bullet": True},
        {"text": f"**Weak spots**: the critic's testability check passes {PROC['pass_round1']['testable']:.0%} of "
                 f"hypotheses, and rank 1 is tied in {PROC['tied_share']:.0%} of questions.", "bullet": True},
        {"text": "**Caveat**: AI judges only; the expert's blind ratings must confirm.", "bullet": True}],
        body_size=12, space=5)


def main() -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = base.W, base.H
    title_slide(prs)
    D10.problem_slide(prs)
    methods_slide(prs)
    overview_slide(prs)
    method_steps(prs)
    output_slide(prs)
    eval_set_slide(prs)
    metrics_slide(prs)
    eval_prompts(prs)
    results_slides(prs)
    prs.save(OUT)
    print(f"wrote {OUT} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
