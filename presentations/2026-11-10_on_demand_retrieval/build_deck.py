"""Build the 2026-11-10 deck: hypothesis generation without an extraction corpus. Literature-extraction pipelines and
their cost; the related methods; our best agent step by step with its prompts and a real run; the evaluation (set,
metrics, prompts) and the results. Reads ../2026-11-04_status/example_trace.json (a real rx_r run), deck_inputs.json
(collect_inputs.py) and methods.json (the related-work table, checked against the papers).

    /tmp/pptx_env/bin/python presentations/2026-11-10_on_demand_retrieval/build_deck.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-11-04_status"))
import build_deck as base  # noqa: E402 - the layout helpers and the example trace of the 4 November deck

from pptx import Presentation  # noqa: E402
from pptx.enum.shapes import MSO_SHAPE  # noqa: E402
from pptx.enum.text import PP_ALIGN  # noqa: E402
from pptx.util import Inches  # noqa: E402

T = base.T
DI = json.loads((HERE / "deck_inputs.json").read_text())
METHODS = json.loads((HERE / "methods.json").read_text())
C, R = DI["cost"], DI["results"]
OUT = HERE / "on_demand_hypothesis_generation_2026-11-10.pptx"
base.FOOTER = "Hypothesis generation without an extraction corpus · high-temperature HEAs · 10 Nov 2026"
NAVY, TEAL, GREEN, RED, AMBER, GRAY = base.NAVY, base.TEAL, base.GREEN, base.RED, base.AMBER, base.GRAY
LIGHT, WHITE, TEXT = base.LIGHT, base.WHITE, base.TEXT
PALE_GREEN, PALE_RED, PALE_TEAL, PALE_AMBER = base.PALE_GREEN, base.PALE_RED, base.PALE_TEAL, base.PALE_AMBER
textbox, rect, card, arrow, table, clip, new_slide = (base.textbox, base.rect, base.card, base.arrow, base.table,
                                                       base.clip, base.new_slide)
MONO = base.MONO


def prompt_box(slide, x, y, w, h, title: str, text: str, size: float = 9.0) -> None:
    rect(slide, x, y, w, h, LIGHT, line=RGB_LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    items = [{"text": title, "size": 11.5, "color": TEAL, "bold": True, "space": 3}]
    lines = text.split("\n")
    items += [{"text": line or " ", "size": size, "font": MONO, "space": 0} for line in lines]
    textbox(slide, x + Inches(0.12), y + Inches(0.08), w - Inches(0.24), h - Inches(0.12), items, space=0)


RGB_LINE = base.RGBColor(0xCB, 0xD5, 0xE1)


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", str(text))


# ---------------------------------------------------------------- part 1: the problem

def title_slide(prs) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    rect(slide, 0, 0, base.W, base.H, NAVY)
    rect(slide, Inches(0.8), Inches(1.9), Inches(0.12), Inches(2.5), TEAL)
    textbox(slide, Inches(1.15), Inches(1.75), Inches(11.4), Inches(1.7),
            "Hypothesis generation without an extraction corpus", size=40, color=WHITE, space=0
            ).text_frame.paragraphs[0].runs[0].font.bold = True
    textbox(slide, Inches(1.15), Inches(2.85), Inches(11.2), Inches(1.6),
            ["Retrieve and read the literature on demand, per research question",
             "Case study: high-temperature high-entropy alloys"], size=21, color=base.RGBColor(0xCB, 0xD5, 0xE1),
            space=4)
    textbox(slide, Inches(1.15), Inches(5.6), Inches(11), Inches(0.9),
            ["The problem with extract-first pipelines · our agent, step by step, with its prompts · evaluation and "
             "results", "10 November 2026 · repository materials-hypothesis-generation (loop.md section 27)"],
            size=14, color=base.RGBColor(0x94, 0xA3, 0xB8), space=4)
    slide.notes_slide.notes_text_frame.text = (
        "Part 1 (slides 2-4): extract-first pipelines and why they do not scale. Part 2 (slides 5-12): our best agent "
        "(rx_r: focused retrieval + conservative writer), one slide per step with its prompt and a real run "
        "(PMC11643467, problem-constrained). Part 3 (slides 14-19): evaluation set, metrics, judge prompts and "
        "results.")


def problem_slide(prs) -> None:
    slide = new_slide(prs, "The problem", "Most hypothesis-generation systems extract first, then generate",
                      section_color=RED, notes=(
                          "Recipe common to the methods on the next slide. Publication volume: about 3 million "
                          "journal articles a year (STM Report 2021) and about 4% growth a year (Bornmann, Haunschild "
                          "and Mutz 2021, Humanities and Social Sciences Communications 8, 224). Our own extraction "
                          "pipeline: 11 evidence roles from a 50-paper corpus (experiments 3-18); the materials "
                          "expert found the extracted data unhelpful, and extracted cards and rubrics did not raise "
                          "the scores of experiments 14-17 (PROJECT_SUMMARY.md section 6)."))
    steps = [("Paper corpus", "thousands to\nhundreds of thousands\nof papers"),
             ("Offline extraction", "an LLM or IE model reads\nevery paper: entities,\ntriples, concepts, roles"),
             ("Structured store", "knowledge graph,\nconcept graph or\nidea database"),
             ("Retrieve", "query the store\nfor a new question"),
             ("Generate", "LLM writes the\nhypothesis")]
    x0, y0, bw, bh, gap = Inches(0.55), Inches(1.45), Inches(2.2), Inches(1.6), Inches(0.31)
    for n, (head, body) in enumerate(steps):
        x = x0 + n * (bw + gap)
        fill = PALE_RED if n in (1, 2) else LIGHT
        rect(slide, x, y0, bw, bh, fill, line=RED if n in (1, 2) else RGB_LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        textbox(slide, x + Inches(0.1), y0 + Inches(0.1), bw - Inches(0.2), bh - Inches(0.15),
                [{"text": f"**{head}**", "size": 15, "color": NAVY, "space": 4}] +
                [{"text": line, "size": 12, "color": TEXT, "space": 0} for line in body.split("\n")],
                align=PP_ALIGN.CENTER)
        if n < 4:
            arrow(slide, x + bw + Inches(0.04), y0 + bh / 2 - Inches(0.1), gap - Inches(0.08), Inches(0.2))
    textbox(slide, Inches(2.6), Inches(3.12), Inches(5.2), Inches(0.35),
            "the costly, corpus-sized step: done before any question is asked", size=11.5, color=RED,
            align=PP_ALIGN.CENTER)
    cards = [
        ("Cost grows with the corpus, not with the question",
         "Every paper is read by a model once per extraction schema and model version, whether or not any question "
         "ever needs it."),
        ("The literature never stops growing",
         "About 3 million journal articles a year, growing about 4% a year. The store must be re-extracted "
         "continuously or it goes stale."),
        ("The schema is fixed before the question",
         "What was extracted decides what can be found. Extraction errors and lost context propagate into every "
         "hypothesis."),
        ("Our own experience",
         "Our first pipeline extracted 11 evidence roles from 50 papers. The materials expert found the extracted "
         "data unhelpful, and extracted cards and rubrics did not raise the scores (experiments 14–17)."),
    ]
    for n, (head, body) in enumerate(cards):
        x = Inches(0.55) + (n % 2) * Inches(6.2)
        y = Inches(3.65) + (n // 2) * Inches(1.65)
        card(slide, x, y, Inches(6.05), Inches(1.5), head, body, PALE_RED if n < 3 else PALE_AMBER,
             RED if n < 3 else AMBER, title_size=14, body_size=12.5)


def methods_slide(prs) -> None:
    slide = new_slide(prs, "The problem", "Recent methods: what each extracts from papers before generating",
                      section_color=RED, notes=METHODS["notes"])
    label = {"yes": "Yes: extraction", "corpus": "Fixed corpus", "no": "No: on demand"}
    shade = {"yes": PALE_RED, "corpus": PALE_AMBER, "no": PALE_GREEN}
    rows = [["Method (venue, year)", "Offline pass?", "Preprocessing: what is extracted, by what, over how many papers",
             "Test set"]]
    fills: list = [None]
    for m in METHODS["rows"]:
        rows.append([f"**{m['method']}** ({m['venue']})", label[m["offline"]], m["extract"], m["test"]])
        fills.append(shade[m["offline"]])
    rows.append(["**Ours: focused on-demand retrieval** (2026)", "**No: on demand**",
                 "**Nothing offline.** Per question: search, screen ~100 abstracts, grade ~160 passages of ~27 full texts",
                 "45 HEA papers (2024–2026), 135 questions, leakage-controlled"])
    fills.append(PALE_GREEN)
    table(slide, Inches(0.55), Inches(1.3), Inches(12.25), rows, [2.85, 1.25, 5.0, 3.15], size=9.5, row_height=0.355,
          fills=fills, header_height=0.32)
    textbox(slide, Inches(0.55), Inches(6.55), Inches(12.25), Inches(0.5), METHODS["footer"], size=10.5, color=GRAY)


def ours_slide(prs) -> None:
    slide = new_slide(prs, "Our approach", "Our agent: no extraction corpus; read on demand, per question",
                      section_color=GREEN, notes=(
                          "Averages over the 135 questions of experiment 44's focused corpora (websearch/focused/"
                          "*/*.json) and the 270 rx_r runs. Papers are parsed from their open-access XML by rules "
                          "(sections into passages); no model reads a paper until a question needs it. 'About 17 "
                          "calls' = 1 search plan + 1 keyword-phrase call + about 6 screening + about 8.5 grading calls."))
    steps = [("1", "Question", "+ knowledge cutoff"), ("2", "Plan searches", "o3-mini · 1 call"),
             ("3", "Search", "Europe PMC ·\n+ 1 Llama-3.3 call"), ("4", "Screen papers", f"gpt-4o · ≈{C['calls_per_question']['screener'] + C['calls_per_question'].get('screener_expansion', 0):.1f} calls"),
             ("5", "Read full texts", "rules · no model"), ("6", "Grade passages",
                                                             f"gpt-4o · ≈{C['calls_per_question']['passage_grader']:.1f} calls"),
             ("7", "Write hypothesis", "o3-mini · 1 call")]
    x0, y0, bw, bh, gap = Inches(0.55), Inches(1.4), Inches(1.56), Inches(1.15), Inches(0.225)
    for n, (num, head, sub) in enumerate(steps):
        x = x0 + n * (bw + gap)
        rect(slide, x, y0, bw, bh, PALE_GREEN if n not in (0,) else LIGHT, line=GREEN,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        textbox(slide, x + Inches(0.05), y0 + Inches(0.07), bw - Inches(0.1), bh - Inches(0.1),
                [{"text": f"**{num} · {head}**", "size": 12, "color": NAVY, "space": 2}] +
                [{"text": s, "size": 10.5, "color": GRAY, "space": 0} for s in sub.split("\n")],
                align=PP_ALIGN.CENTER)
        if n < 6:
            arrow(slide, x + bw + Inches(0.02), y0 + bh / 2 - Inches(0.08), gap - Inches(0.04), Inches(0.16))
    funnel_slide_body(slide)
    card(slide, Inches(7.45), Inches(2.85), Inches(5.35), Inches(3.95), "Why this scales",
         [{"text": "**No offline pass.** Nothing is extracted before a question is asked; a new paper is usable as "
                   "soon as the search index has it.", "bullet": True},
          {"text": f"**Bounded cost per question:** about {C['retrieval_calls_per_question'] + 1:.0f} small model "
                   "calls (search phrases, titles and abstracts, passages) and one writer call, whatever the size "
                   "of the literature.", "bullet": True},
          {"text": "**The model reads the source text,** not a lossy extraction made for a schema chosen in "
                   "advance.", "bullet": True},
          {"text": f"**Leakage-safe by construction:** every search is filtered to papers dated before the target "
                   f"paper. Over 135 questions, {C['distinct_papers_used']:,} distinct papers were used.",
           "bullet": True}], PALE_GREEN, GREEN, body_size=13, space=8)


def funnel_slide_body(slide) -> None:
    """Slide 4's funnel: what happens to one question, in plain words, as shrinking bars."""
    textbox(slide, Inches(0.55), Inches(2.72), Inches(6.7), Inches(0.35),
            "**What happens to one question** (average over our 135 test questions)", size=13, color=NAVY, space=0)
    stages = [
        (f"{C['search_hits_per_question'] + C['earlier_corpus_papers_per_question']:.0f}", "papers found",
         "by the planned searches and a broad keyword search (a few twice)", GRAY),
        (f"{C['admitted_per_question']:.0f}", "pass the rules",
         "published before the cutoff, open access, a research article", GRAY),
        (f"{C['screened_per_question']:.0f}", "titles + abstracts read",
         "by gpt-4o, which grades each 0–3 for relevance", TEAL),
        (f"{C['papers_kept_per_question']:.0f}", "papers kept",
         "graded relevant; only these are opened in full", TEAL),
        (f"{C['passages_graded_per_question']:.0f}", "passages read",
         "the 6 best sections of each kept paper, graded by gpt-4o", TEAL),
        (f"{C['pack_passages_per_question']:.0f}", "passages to the writer",
         f"the most relevant ones, ≈ {C['pack_chars_per_question'] / 1000:.0f}k characters (≈ 15 pages)", GREEN),
    ]
    top = float(stages[0][0])
    y = Inches(3.12)
    for count, head, body, color in stages:
        width = Inches(0.55 + 1.65 * (float(count) / top) ** 0.5)
        rect(slide, Inches(0.55), y, width, Inches(0.5), color, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        textbox(slide, Inches(0.55), y + Inches(0.06), width, Inches(0.4), f"**{count}**", size=15, color=WHITE,
                align=PP_ALIGN.CENTER, space=0)
        textbox(slide, Inches(2.85), y + Inches(0.0), Inches(4.45), Inches(0.55),
                [{"text": f"**{head}**", "size": 12.5, "space": 0},
                 {"text": body, "size": 10.5, "color": GRAY, "space": 0}], space=0)
        y += Inches(0.6)


def search_slides(prs, s1: dict, s2: dict) -> None:
    """Step 3 on two slides: the planned searches (3a) and the broad keyword search with the rule checks (3b)."""
    groups = s1["output_parsed"]["groups"]
    searches = s2["searches"]
    slide = new_slide(prs, "Our agent · step 3a of 7", "Search Europe PMC with the planned searches (no model)",
                      section_color=GREEN, notes=(
                          "focused_search.query_for builds each query; focused_search.run_searches runs it on Europe "
                          "PMC (titles and abstracts, TITLE_ABS) and, for a three-group search with fewer than 3 "
                          "results, retries with the first two groups. websearch.filters adds the access and date "
                          "filters. No model is called in this step."))
    textbox(slide, Inches(0.55), Inches(1.32), Inches(6.0), Inches(2.75), [
        {"text": "**How one search is built**", "size": 13.5, "color": GREEN, "space": 4},
        {"text": "Each **group** from step 2 is a list of synonyms, joined with **OR** (any of them may appear).",
         "bullet": True, "size": 12.5},
        {"text": "A **search** joins 2 or 3 groups with **AND** (each group must be matched), in the title or "
                 "abstract.", "bullet": True, "size": 12.5},
        {"text": "Every search adds the same filters: open access, full text available, not a preprint, published "
                 "before the cutoff (2024-11-30 here).", "bullet": True, "size": 12.5},
        {"text": "No model is involved: these are plain database queries.", "bullet": True, "size": 12.5}],
        space=4)
    first = searches[0]
    example = ("(" + " OR ".join(groups[first["groups"][0]]) + ")\n  AND\n(" + " OR ".join(groups[first["groups"][1]])
               + ")\n  AND open access, full text, published before 2024-11-30")
    prompt_box(slide, Inches(6.8), Inches(1.32), Inches(6.0), Inches(2.75),
               f"Example: the search “{first['groups'][0]} AND {first['groups'][1]}” → {first['hit_count']} papers",
               example, size=11)
    back = next(x for x in searches if len(x["requested"]) == 3)
    card(slide, Inches(0.55), Inches(4.25), Inches(6.0), Inches(2.65), "What a “3-group search” is, and the back-off",
         [{"text": f"A 3-group search requires all three groups at once, e.g. **{' AND '.join(back['requested'])}**.",
           "bullet": True},
          {"text": "Three conditions together are often too narrow. **If it finds fewer than 3 papers, the third group "
                   "is dropped** and the search is rerun with the first two.", "bullet": True},
          {"text": f"In this run: {' AND '.join(back['requested'])} → rerun as {' AND '.join(back['groups'])} → "
                   f"{back['hit_count']} papers.", "bullet": True}], PALE_TEAL, TEAL, body_size=12, space=4)
    rows = [["The 8 searches of this run", "Papers"]]
    for x in searches:
        label = " AND ".join(x["groups"]) + (" (dropped " + x["requested"][-1] + ")" if x["requested"] != x["groups"]
                                              else "")
        rows.append([label, f"{x['hit_count']}" + (f" (first {x['fetched']} used)" if x["fetched"] < x["hit_count"]
                                                     else "")])
    table(slide, Inches(6.8), Inches(4.25), Inches(6.0), rows, [4.35, 1.65], size=10, row_height=0.27,
          header_height=0.3)

    oc = s2["old_corpus_channel"]
    slide = new_slide(prs, "Our agent · step 3b of 7", "A second, broad keyword search, then the rule checks",
                      section_color=GREEN, notes=(
                          "websearch.phrases_for (Llama-3.3, one call per question; temperature 0) and "
                          "websearch.build_corpus: each phrase becomes an OR of its words in the abstract, combined "
                          "with high-entropy-alloy terms; the matches are ranked by word overlap with the question; "
                          "the first 50 with full text are kept, plus up to 50 references cited by at least two of "
                          "them. Rule checks: websearch.admit (Europe PMC and Crossref records)."))
    textbox(slide, Inches(0.55), Inches(1.32), Inches(6.0), Inches(3.0), [
        {"text": "**Why a second search?**", "size": 13.5, "color": GREEN, "space": 4},
        {"text": "The planned searches are precise but can miss papers: here 4 of the 8 found 0 or 1 paper.",
         "bullet": True, "size": 12.5},
        {"text": "So the agent also runs a broad keyword search, which casts a wider net.", "bullet": True,
         "size": 12.5},
        {"text": "**This is where the prompt comes in:** a model (Llama-3.3, 1 call) writes the three keyword "
                 "phrases from the question. Everything after that is plain database search.", "bullet": True,
         "size": 12.5},
        {"text": "Each phrase finds papers whose abstract mentions any of its words and is about high-entropy "
                 "alloys. The best-matching 50 papers are kept, plus papers often cited by them.", "bullet": True,
         "size": 12.5}], space=4)
    prompt_box(slide, Inches(6.8), Inches(1.32), Inches(6.0), Inches(3.0),
               "Prompt: keyword phrases (Llama-3.3, 1 call, verbatim)",
               oc["system"] + "\n\nOutput for this question:\n" + "\n".join(f"• {x}" for x in oc["output"]["phrases"]),
               size=10.5)
    card(slide, Inches(0.55), Inches(4.5), Inches(6.0), Inches(2.4), "Rule checks on every paper (code, no model)",
         [{"text": "Published before the cutoff, by two date sources (Europe PMC and Crossref).", "bullet": True},
          {"text": "A research article (not a review, editorial or preprint), with open-access full text.",
           "bullet": True},
          {"text": "Not the hidden paper itself, nor a closely related paper by the same authors.", "bullet": True}],
         PALE_TEAL, TEAL, body_size=12, space=4)
    both = s2["channels"].get("both", 0)
    card(slide, Inches(6.8), Inches(4.5), Inches(6.0), Inches(2.4), "Real run (the zirconium paper)",
         [f"Planned searches: **{s2['unique_hits']}** papers. Broad keyword search: **{oc['papers']}** papers "
          f"(about {both} found by both).",
          f"After the rule checks: **{s2['admitted']}** papers ({', '.join(f'{v} {k.replace(chr(95), chr(32))}' for k, v in s2['rejected'].items())}).",
          "These go to step 4, where gpt-4o reads their titles and abstracts."],
         PALE_TEAL, TEAL, body_size=12.5, space=5)


# ---------------------------------------------------------------- part 2: the agent, step by step

def step_slide(prs, number: int, title: str, what: list, prompt_title: str, prompt: str, example: list,
               notes: str, prompt_size: float = 9.0, left_w: float = 5.5) -> None:
    slide = new_slide(prs, f"Our agent · step {number} of 7", title, section_color=GREEN, notes=notes)
    textbox(slide, Inches(0.55), Inches(1.35), Inches(left_w), Inches(2.6),
            [{"text": "**What happens**", "size": 13, "color": GREEN, "space": 4}] +
            [{"text": w, "bullet": True, "size": 12.5, "bullet_color": GREEN, "space": 4} for w in what], space=4)
    card(slide, Inches(0.55), Inches(4.05), Inches(left_w), Inches(2.85), "Real run (the zirconium paper)",
         example, PALE_TEAL, TEAL, body_size=11.5, space=3)
    prompt_box(slide, Inches(0.55 + left_w + 0.25), Inches(1.35), Inches(12.25 - left_w - 0.25), Inches(5.55),
               prompt_title, prompt, size=prompt_size)


def agent_steps(prs) -> None:
    s0, s1, s2, s3 = (T["stage0_benchmark_case"], T["stage1_search_plan"], T["stage2_search"], T["stage3_screening"])
    s4, s5 = T["stage4_passages"], T["stage5_writer"]
    question = T["user_input"]["question"]
    step_slide(prs, 1, "The input: a research question and a knowledge cutoff", [
        "The user asks one research question; nothing else is given: no paper, no corpus, no extracted data.",
        "The knowledge cutoff is the date before which all evidence must be published (here, the hidden paper's "
        "publication date).",
        "In the benchmark the question comes from a held-out paper's introduction, with the paper's own "
        "contribution removed and leakage checked."],
        "Input to the agent (JSON)",
        json.dumps({"query": question, "knowledge_cutoff": T["user_input"]["knowledge_cutoff"]}, indent=1,
                   ensure_ascii=False),
        [f"Hidden paper: “{T['paper']['title'].rstrip('.')}”, {T['paper']['publication_date']}.",
         "The question never names zirconium, the paper's intervention.",
         f"Leakage checker: {len(s0['question']['checks_and_lexical_gate']['problem_constrained']['leaks'])} "
         f"leaking phrases; answer-word overlap "
         f"{s0['question']['checks_and_lexical_gate']['problem_constrained']['overlap']:.1%} (gate ≤ 10%)."],
        notes="The question is the problem-constrained level of PMC11643467 (test4). The JSON on the right is "
              "exactly what the agent receives; the prompts of the following steps add their own instructions.",
        prompt_size=11)
    groups = s1["output_parsed"]["groups"]
    step_slide(prs, 2, "Plan the searches (o3-mini, 1 call)", [
        "o3-mini turns the question into groups of short search phrases: material, material class, property, "
        "regime, and up to six approaches a researcher would look up.",
        "It then combines groups into 6–8 searches, from specific (material AND property) to broad (class AND "
        "approach).",
        "Code cleans the phrases (1–4 words) and keeps only valid searches; one retry if none is usable."],
        "Prompt: search planner (PLAN_SYSTEM, verbatim)", s1["system"],
        [f"**{k}:** {', '.join(v)}" for k, v in list(groups.items())[:7]] +
        [f"… {len(groups)} groups, {len(s1['output_parsed']['searches'])} searches."],
        notes="Output shown as parsed by focused_search.parse_plan (stored in the question's manifest).",
        prompt_size=9.5)
    search_slides(prs, s1, s2)
    graded = [(g["grade"], g["why"], p["title"]) for b in s3["batches"]
              for p, g in zip(b["input"]["papers"], b["output_parsed"]["grades"])]
    counts = {k: sum(1 for g in graded if g[0] == k) for k in (3, 2, 1, 0)}
    picks = [next(g for g in graded if g[0] == k) for k in (3, 2, 1, 0)]
    step_slide(prs, 4, "Screen titles and abstracts (gpt-4o)", [
        "Admitted papers are ordered by word match with the plan (BM25); the top 120 are screened.",
        "gpt-4o grades each paper 0–3 for usefulness to the question, 20 per call, in a seeded random order with "
        "neutral numbers (no position bias, no IDs).",
        "Papers graded 2 or 3 are kept (at most 30). References co-cited by at least two kept papers are screened "
        "the same way and may add up to 10."],
        "Prompt: paper screener (SCREEN_SYSTEM, verbatim)", s3["system"],
        [f"Grades: 3 → {counts[3]}, 2 → {counts[2]}, 1 → {counts[1]}, 0 → {counts[0]}; "
         f"{len(s3['selected_papers'])} papers kept."] +
        [f"**{g}** · {clip(strip_tags(t), 70)} — “{clip(w, 50)}”" for g, w, t in picks],
        notes="Input per paper: {id, title, abstract (first 1,500 characters)}; output {grades: [{id, grade, why}]}. "
              "A paper the screener does not grade gets 0.", prompt_size=10)
    first = s4["batches"][0]["input"]["passages"][0]
    step_slide(prs, 5, "Read the kept papers' full text (rules, no model)", [
        "Only now is a paper's full text opened: its open-access XML is split by section into passages of at most "
        "1,600 characters.",
        "No model reads the paper; no fields are extracted; nothing is stored for later questions except the cache "
        "of downloaded files.",
        "BM25 on the plan's phrases (never the question template) picks each paper's 6 best passages."],
        "Rule (code, not a prompt)",
        "for paper in kept_papers:               # ~27 per question\n"
        "    xml = full_text(paper)              # open-access XML\n"
        "    passages = split_by_section(xml,    # verbatim text,\n"
        "                   max_chars=1600)      # section-aligned\n"
        "    candidates += bm25(plan_phrases,\n"
        "                       passages)[:6]    # 6 per paper\n"
        "# ~160 candidate passages per question\n\n"
        "Each passage keeps: paper title, section, publication date, text.\n"
        "Passages are later shown to models with neutral labels only.",
        [f"{len(s4['batches'])} batches · {sum(len(b['record_ids']) for b in s4['batches'])} candidate passages from "
         f"{len(s3['selected_papers'])} papers.",
         f"Example candidate: “{clip(first['section'], 40)}” of “{clip(strip_tags(first['paper_title']), 60)}”:",
         f"“{clip(first['text'], 230)}”"],
        notes="focused_search.paper_records (websearch.passages) and focused_search.rank_passages. Template words of "
              "the question are excluded from BM25 terms (experiment 42 finding).", prompt_size=11)
    pg = {k: sum(1 for b in s4["batches"] for g in b["output_parsed"]["grades"] if g["grade"] == k)
          for k in (3, 2, 1, 0)}
    step_slide(prs, 6, "Grade passages and pack the evidence (gpt-4o)", [
        "gpt-4o grades each candidate passage 0–3 for the question, 20 per call, shuffled, neutral numbers.",
        "The pack takes grade-3 passages, then grade-2, ordered by their paper's grade, until 64,000 characters "
        "(at most 96 passages).",
        "Every passage in the pack keeps an ID the writer must cite; unknown IDs are removed."],
        "Prompt: passage grader (PASSAGE_SYSTEM, verbatim)", s4["system"],
        [f"Grades: 3 → {pg[3]}, 2 → {pg[2]}, 1 → {pg[1]}, 0 → {pg[0]}.",
         f"Pack: {len(s4['pack'])} passages, {s4['pack_chars']:,} characters, from "
         f"{len({r.split('::')[0] for r in s4['pack']})} papers.",
         "Across all 135 questions, 77% of graded passages are relevant (grade 2 or 3)."],
        notes="focused_search.grade_passages and focused_search.pack. 77% = (9,639 + 7,292) / 22,008 graded passages.",
        prompt_size=10.5)
    g = s5["output"]
    step_slide(prs, 7, "Write the hypothesis (o3-mini, 1 call)", [
        "o3-mini receives the question, the cutoff and the 46 passages (title, section, date, text) and writes one "
        "falsifiable hypothesis in a fixed schema.",
        "The prompt is conservative: predict only as far as the evidence supports, state uncertainty instead of "
        "inventing values, cite only supplied IDs.",
        f"Input {s5['trace'][0]['chars_in']:,} characters; {s5['trace'][0]['seconds']:.0f} s."],
        "Prompt: writer (WRITER_B with the output schema, verbatim)", s5["system"],
        [f"**Hypothesis:** {clip(g['hypothesis'], 200)}",
         f"**Intervention:** {clip(g['intervention'], 120)}",
         f"**Mechanism:** {clip(g['mechanism'], 150)}",
         f"**Falsification rule:** {clip(g['falsification_experiment']['falsification_rule'], 120)}",
         "Cites 2 passages of a 2023 paper on Y/Hf co-doped AlCoCrFeNi2.1 coatings."],
        notes="loop_methods.WRITER_B via Harness.generate_final with citation repair by filtering. The full output "
              "is in ../2026-11-04_status/example_trace.md, section 5.", prompt_size=8.5)


# ---------------------------------------------------------------- part 3: evaluation and results

def eval_set_slide(prs) -> None:
    slide = new_slide(prs, "Evaluation", "Evaluation set and protocol", section_color=NAVY, notes=(
        "Sets: dev 8 (2024), test 4, test2 12, test3 12, test4 9 papers; published 2024-01 to 2026-07. All 45 were "
        "used for development after their pre-registered finals, so the results are development results; a clean "
        "claim needs fresh papers (test5). Leakage: must_obey.md sections 2-5; loop.md 25-27."))
    rows = [["Set", "Papers", "Published"], ["dev", "8", "Jan–Nov 2024"], ["test", "4", "Apr 2025 – Feb 2026"],
            ["test2", "12", "Jul 2025 – Jul 2026"], ["test3", "12", "Jan 2024 – Jun 2025"],
            ["test4", "9", "Nov 2024 – Mar 2026"], ["**Total**", "**45**", "Jan 2024 – Jul 2026"]]
    table(slide, Inches(0.55), Inches(1.4), Inches(5.0), rows, [1.3, 1.1, 2.6], size=12.5, row_height=0.42)
    textbox(slide, Inches(0.55), Inches(4.55), Inches(5.0), Inches(2.3), [
        {"text": "**45 papers × 3 question levels = 135 questions**", "size": 15, "space": 4},
        {"text": "Levels: broad · problem-constrained · expert context", "size": 12.5, "color": GRAY, "space": 6},
        {"text": "**× 2 samples = 270 hypotheses per method**", "size": 15, "space": 4},
        {"text": f"{R['configurations']} methods scored (13,500 hypotheses)", "size": 12.5, "color": GRAY}])
    card(slide, Inches(5.85), Inches(1.4), Inches(6.95), Inches(5.45), "How leakage is prevented", [
        {"text": "**Questions** are written by GPT-5.6 from the paper's introduction with every sentence about the "
                 "paper's own work removed; a separate checker that sees the answer flags leaking phrases; "
                 "answer-word overlap must be ≤ 10%.", "bullet": True},
        {"text": "**Only models trained before the paper** answer: o3-mini, gpt-4o, o1, Llama-3.3 (cutoffs 2023).",
         "bullet": True},
        {"text": "**Evidence dated before the paper**, checked by Europe PMC and Crossref dates; the paper, its DOI "
                 "and title are blocked from every model input.", "bullet": True},
        {"text": "**Judges are blinded**: neutral evidence labels, shuffled candidates, both presentation orders.",
         "bullet": True},
        {"text": "Every retrieved record is re-checked after the run: 0 leaks.", "bullet": True},
        {"text": "**Caveat:** all 45 papers have been used during development; a clean claim needs a fresh set.",
         "bullet": True, "bullet_color": AMBER}], PALE_TEAL, NAVY, body_size=13, space=7)


def metrics_slide(prs) -> None:
    g, v = R["grounding_validation"], R
    slide = new_slide(prs, "Evaluation", "Metrics: how strong is the research proposal?", section_color=NAVY, notes=(
        "SP and the decision rule: must_obey.md 6.2 (amended 2026-11-05) and loop.md 27.1. Validation results: loop.md "
        "27.2. The answer key is not used by any metric; it only builds and leak-checks the questions."))
    card(slide, Inches(0.55), Inches(1.4), Inches(6.1), Inches(2.6), "Strong-proposal score, SP (0–4)", [
        {"text": "SP = mean(plausibility, testability, usefulness, grounding) − 1", "size": 14, "font": MONO,
         "space": 8},
        {"text": "**Plausibility, testability, usefulness** (1–5): the materials expert's own blind scales, judged "
                 "by DeepSeek-V4-Pro, mean of 3 calls.", "bullet": True},
        {"text": "**Grounding** (1–5): are the hypothesis's key premises supported by the passages it cites? "
                 "DeepSeek-V4-Pro, 1 call.", "bullet": True}], PALE_TEAL, TEAL, body_size=12.5, space=4)
    card(slide, Inches(6.85), Inches(1.4), Inches(5.95), Inches(2.6), "Decisions: pairwise preference", [
        {"text": "Each method's hypothesis vs the closed-book writer's, for the same question and sample.",
         "bullet": True},
        {"text": "Shown in both orders; a win needs both. Net preference per paper, 95% CI over papers.",
         "bullet": True},
        {"text": "**DeepSeek** decides during development; **GPT-5.6** is held out to confirm; **o1** alongside.",
         "bullet": True}], PALE_TEAL, TEAL, body_size=12.5, space=4)
    rows = [["Check of the measure (before use)", "Result", "Pass"],
            ["Grounding: another paper's passages swapped in", f"{v['g1']['original_mean']:.2f} → "
                                                              f"{v['g1']['control_mean']:.2f}", "✓"],
            ["Grounding: every citation removed", f"mean {v['g2']['control_mean']:.2f} (≤ 1.5)", "✓"],
            ["Grounding: same runs judged again", f"Spearman {g['G3_retest']['rho']:.2f} (≥ 0.70)", "✓"],
            ["Grounding: evidence writer vs closed-book writer", f"+{v['g4']['diff']:.2f} "
                                                                 f"[+{v['g4']['ci95'][0]:.2f}, +{v['g4']['ci95'][1]:.2f}]",
             "✓"],
            ["RQ sanity controls: good vs generic hypotheses", f"+{v['controls']['gaps']['rq_positive_minus_generic']:.2f}"
                                                               " (≥ 1)", "✓"],
            ["RQ sanity controls: good vs random-question hypotheses",
             f"usefulness +{v['controls']['gaps']['usefulness_positive_minus_random']:.2f} (≥ 1)", "✓"]]
    table(slide, Inches(0.55), Inches(4.2), Inches(12.25), rows, [6.4, 4.85, 1.0], size=11.5, row_height=0.37)


def eval_prompts(prs) -> None:
    p = DI["prompts"]
    rq = p["RQ_SYSTEM"]
    cut = rq.index("Rate the hypothesis on three")
    slide = new_slide(prs, "Evaluation · prompts (verbatim)", "Research-quality judge (DeepSeek, 3 calls per hypothesis)",
                      section_color=GRAY, notes=(
                          "rq_judge.RQ_SYSTEM: the expert package's instructions and scales, verbatim (loop.md 24.1). "
                          "Input: {research_question, hypothesis rendered as the expert sees it}; no citations, no "
                          "evidence, no answer key."))
    prompt_box(slide, Inches(0.55), Inches(1.35), Inches(6.05), Inches(5.6), "RQ judge (1/2)", rq[:cut].rstrip(),
               size=8.5)
    prompt_box(slide, Inches(6.75), Inches(1.35), Inches(6.05), Inches(5.6), "RQ judge (2/2)", rq[cut:], size=8.5)
    slide = new_slide(prs, "Evaluation · prompts (verbatim)", "Grounding judge and pairwise judge", section_color=GRAY,
                      notes=("quality_eval.GROUNDING_SYSTEM (input: question, hypothesis as JSON with evidence IDs "
                             "relabelled E1, E2, …, and the cited passages) and diag_analysis.QUALITY_PAIR_SYSTEM "
                             "(input: question and two candidates, each with its cited passages; run in both orders)."))
    prompt_box(slide, Inches(0.55), Inches(1.35), Inches(6.05), Inches(5.6), "Grounding judge (DeepSeek, 1 call)",
               p["GROUNDING_SYSTEM"], size=9)
    prompt_box(slide, Inches(6.75), Inches(1.35), Inches(6.05), Inches(5.6),
               "Pairwise judge (DeepSeek · GPT-5.6 · o1, both orders)", p["QUALITY_PAIR_SYSTEM"], size=10)


def c(x: dict) -> str:
    if not x or not x.get("papers"):
        return "–"
    return f"{x['diff']:+.2f} ({x['up']} vs {x['down']})"


def results_slides(prs) -> None:
    rows_data = R["rows"]
    order = [("rx_r", "**Our agent: focused on-demand retrieval + writer**"),
             ("edit_rx_r", "+ an editing pass"), ("rx_ru", "+ a literature-map prompt"),
             ("rx_ruc", "+ a multi-critic refinement loop"),
             ("agent_draft_ground_b_o3mini", "Agent that drafts, then retrieves evidence"),
             ("rx_base", "Earlier per-question web corpus (unscreened) + writer"),
             ("web_text_64k_b_o3mini", "Same corpus, original ranking (experiment 36)"),
             ("writer_only_b_o3mini", "Closed-book writer (no retrieval)"),
             ("closed_book", "Llama-3.3 baseline")]
    slide = new_slide(prs, "Results", "Results: on-demand focused retrieval gives the strongest proposals",
                      section_color=GREEN, notes=(
                          "loop_quality/analysis_quality.md (experiment 46, phase 1; loop.md 27.4). Pairwise = net "
                          "preference over the closed-book writer, per paper, both orders must agree; in brackets: "
                          "papers in which each side is preferred (out of 45). GPT-5.6 confirmed only the top three. "
                          "50 configurations were scored; the 9 rows shown include the best, the closest variants "
                          "and the baselines."))
    rows = [["Method", "SP", "Plaus.", "Test.", "Useful.", "Ground.", "Pairwise vs closed-book: DeepSeek",
             "o1", "GPT-5.6"]]
    fills = [None]
    for m, label in order:
        x = rows_data[m]
        s = x["scales"]
        p = x["pairwise"]
        rows.append([label, f"**{x['sp']:.2f}**" if m == "rx_r" else f"{x['sp']:.2f}", f"{s['plausibility']:.2f}",
                     f"{s['testability']:.2f}", f"{s['usefulness']:.2f}", f"{x['grounding']:.2f}",
                     "(reference)" if m == "writer_only_b_o3mini" else c(p.get("deepseek")),
                     "" if m == "writer_only_b_o3mini" else c(p.get("o1")),
                     "" if m == "writer_only_b_o3mini" else c(p.get("gpt56"))])
        fills.append(PALE_GREEN if m == "rx_r" else None)
    ref = R["references"]["oracle_hint_full_b_o3mini"]
    rows.append(["Reference: the authors' own study, written as a proposal", f"{ref['sp']:.2f}", "", "", "",
                 f"{ref['grounding']:.2f}", c(ref["pairwise"].get("deepseek")), "", ""])
    fills.append(PALE_AMBER)
    table(slide, Inches(0.55), Inches(1.35), Inches(12.25), rows, [4.0, 0.7, 0.75, 0.7, 0.8, 0.8, 2.05, 1.25, 1.2],
          size=10.5, row_height=0.43, fills=fills)
    textbox(slide, Inches(0.55), Inches(6.3), Inches(12.25), Inches(0.65),
            "SP on 0–4; the four scales on 1–5. 45 papers, 135 questions, 270 hypotheses per method. Pairwise in "
            "brackets: papers in which each side is preferred.", size=11, color=GRAY)

    x = rows_data["rx_r"]
    slide = new_slide(prs, "Results", "What the results say", section_color=GREEN, notes=(
        "Scales of rx_r: plausibility 3.56, testability 4.19, usefulness 4.35, grounding 2.52 (1-5). Among o3-mini "
        "configurations all 25 that cite evidence score SP >= 2.37 and all 18 closed-book ones <= 2.37 (loop.md "
        "27.4). Llama-3.3 configurations are well grounded (2.22-2.45) but score 1.10-1.34."))
    base.bar_chart(slide, Inches(0.45), Inches(1.35), Inches(6.3), Inches(3.4), "Our agent's four scales (1–5)",
                   ["Usefulness", "Testability", "Plausibility", "Grounding"],
                   [x["scales"]["usefulness"], x["scales"]["testability"], x["scales"]["plausibility"],
                    x["grounding"]], [GREEN, GREEN, AMBER, RED], maximum=5.0, cat_size=12)
    p = x["pairwise"]
    textbox(slide, Inches(0.55), Inches(4.9), Inches(6.2), Inches(2.0), [
        {"text": "**Preferred over the closed-book writer by all three judges**", "size": 13.5, "space": 4},
        {"text": f"DeepSeek {p['deepseek']['diff']:+.2f}: {p['deepseek']['up']} papers vs {p['deepseek']['down']}",
         "bullet": True, "size": 12.5},
        {"text": f"o1 {p['o1']['diff']:+.2f}: {p['o1']['up']} vs {p['o1']['down']}", "bullet": True, "size": 12.5},
        {"text": f"GPT-5.6 (held out) {p['gpt56']['diff']:+.2f}: {p['gpt56']['up']} vs {p['gpt56']['down']}",
         "bullet": True, "size": 12.5}], space=3)
    card(slide, Inches(7.0), Inches(1.4), Inches(5.8), Inches(5.5), "Findings", [
        {"text": "**Reading relevant sources on demand gives the strongest proposals**: SP 2.65 vs 2.33 closed-book; "
                 "best of 50 methods.", "bullet": True},
        {"text": "**Relevance matters**: screened, focused evidence beats the unscreened per-question corpus with the "
                 "same writer (2.65 vs 2.54; grounding 2.52 vs 2.00).", "bullet": True},
        {"text": "**More machinery does not help**: editing, literature maps, critique loops, agents add nothing on "
                 "top of focused retrieval.", "bullet": True},
        {"text": "**No extraction corpus was needed** at any point.", "bullet": True},
        {"text": "**Weakest scale: grounding** (2.52 of 5): about half of the key premises are not supported by the "
                 "passages cited. Next target.", "bullet": True, "bullet_color": AMBER},
        {"text": "**Caveat**: AI judges, which prefer the AI proposals to the authors' own studies (−0.17); the "
                 "expert's blind ratings must confirm.", "bullet": True, "bullet_color": RED}],
         PALE_GREEN, GREEN, body_size=13, space=7)


def closing_slide(prs) -> None:
    slide = new_slide(prs, "Summary", "Summary and next steps", section_color=TEAL, notes=(
        "Next steps follow loop.md 27.1 (phases 2-4)."))
    card(slide, Inches(0.55), Inches(1.4), Inches(6.0), Inches(5.0), "Summary", [
        {"text": "Extract-first pipelines pay a corpus-sized extraction cost up front, and again as the literature "
                 "grows.", "bullet": True},
        {"text": "Our agent extracts nothing in advance: per question it searches, screens ~100 abstracts, reads "
                 "~27 full texts and grades ~160 passages, then writes.", "bullet": True},
        {"text": "It gives the strongest proposals of 50 methods (SP 2.65 / 4), preferred by all three judges over "
                 "the closed-book writer.", "bullet": True}], PALE_TEAL, TEAL, body_size=15, space=10)
    card(slide, Inches(6.8), Inches(1.4), Inches(6.0), Inches(5.0), "Next steps", [
        {"text": "**Grounding**: make the writer support each key premise with a passage (weakest scale).",
         "bullet": True},
        {"text": "**Cost comparison**: run an extract-first baseline on the same questions and compare quality per "
                 "model call.", "bullet": True},
        {"text": "**Expert ratings**: confirm the AI judges against the materials expert.", "bullet": True},
        {"text": "**Fresh papers**: a new held-out set for a clean claim.", "bullet": True}],
         PALE_AMBER, AMBER, body_size=15, space=10)


def main() -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = base.W, base.H
    title_slide(prs)
    problem_slide(prs)
    methods_slide(prs)
    ours_slide(prs)
    agent_steps(prs)
    eval_set_slide(prs)
    metrics_slide(prs)
    eval_prompts(prs)
    results_slides(prs)
    closing_slide(prs)
    prs.save(OUT)
    print(f"wrote {OUT} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
