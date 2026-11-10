"""Build the 2026-11-10 deck: hypothesis generation without an extraction corpus. Literature-extraction pipelines and
their cost; the related methods; our best agent step by step with its prompts and a real run; the evaluation (set,
metrics, prompts) and the results. The agent is the draft-then-ground agent (agent_draft_ground_b_o3mini). Reads
draft_example.json (a logged demonstration run, draft_example.py), ../2026-11-04_status/example_trace.json (the
benchmark case), deck_inputs.json (collect_inputs.py) and methods.json (the related-work table).

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
CD, R = DI["cost_draft"], DI["results"]
EX = json.loads((HERE / "draft_example.json").read_text())
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
        "Part 1 (slides 2-3): extract-first pipelines and why they do not scale. Part 2 (slides 4-9): our agent "
        "(draft-then-ground: o3-mini drafts an idea, then reads on-demand retrieved passages and rewrites it), one "
        "slide per step with its prompt and a logged run (PMC11643467, problem-constrained). Part 3 (slides 10-16): "
        "evaluation set, metrics, judge prompts and results.")


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
    rows.append(["**Ours: draft, then read on demand** (2026)", "**No: on demand**",
                 f"**Nothing offline.** Per question: o3-mini drafts an idea; a keyword search opens "
                 f"~{CD['corpus_papers']:.0f} full texts; the ~{CD['pack_passages']:.0f} passages closest to the "
                 f"draft are read; the idea is rewritten",
                 "45 HEA papers (2024–2026), 135 questions, leakage-controlled"])
    fills.append(PALE_GREEN)
    table(slide, Inches(0.55), Inches(1.3), Inches(12.25), rows, [2.85, 1.25, 5.0, 3.15], size=9.5, row_height=0.355,
          fills=fills, header_height=0.32)
    textbox(slide, Inches(0.55), Inches(6.55), Inches(12.25), Inches(0.5), METHODS["footer"], size=10.5, color=GRAY)


def ours_slide(prs) -> None:
    slide = new_slide(prs, "Our approach", "Our agent: draft first, then read the literature on demand",
                      section_color=GREEN, notes=(
                          "The draft-then-ground agent (agent_draft_ground_b_o3mini). Averages over the 135 questions "
                          "(deck_inputs.json, cost_draft): the per-question keyword search and its corpus, and the "
                          "agent's 270 stored runs. Papers are split into passages by rules from their open-access "
                          "XML; no model reads a paper in advance. Model calls per question: 1 Llama-3.3 call for "
                          "the keyword phrases (shared by both samples of a question) and 2 o3-mini calls per "
                          "hypothesis (2.2 on average, with occasional repair calls)."))
    steps = [("1", "Question", "+ knowledge cutoff"), ("2", "Draft an idea", "o3-mini · 1 call ·\nno evidence"),
             ("3", "Search", "Llama-3.3 phrases ·\nEurope PMC"), ("4", "Read & rank", "rules · no model"),
             ("5", "Rewrite with evidence", "o3-mini · 1 call")]
    x0, y0, bw, bh, gap = Inches(0.55), Inches(1.4), Inches(2.2), Inches(1.15), Inches(0.31)
    for n, (num, head, sub) in enumerate(steps):
        x = x0 + n * (bw + gap)
        rect(slide, x, y0, bw, bh, PALE_GREEN if n else LIGHT, line=GREEN, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        textbox(slide, x + Inches(0.05), y0 + Inches(0.07), bw - Inches(0.1), bh - Inches(0.1),
                [{"text": f"**{num} · {head}**", "size": 13, "color": NAVY, "space": 2}] +
                [{"text": s, "size": 11, "color": GRAY, "space": 0} for s in sub.split("\n")],
                align=PP_ALIGN.CENTER)
        if n < 4:
            arrow(slide, x + bw + Inches(0.04), y0 + bh / 2 - Inches(0.09), gap - Inches(0.08), Inches(0.18))
    funnel_slide_body(slide)
    card(slide, Inches(7.45), Inches(2.85), Inches(5.35), Inches(3.95), "Why this scales",
         [{"text": "**No offline pass.** Nothing is extracted before a question is asked; a new paper is usable as "
                   "soon as the search index has it.", "bullet": True},
          {"text": "**Three model calls per question**, whatever the size of the literature: one to write search "
                   "phrases, one to draft, one to rewrite. Reading and ranking the papers needs no model.",
           "bullet": True},
          {"text": "**The idea comes first.** The agent drafts its own idea, then reads only the evidence that bears "
                   "on it, instead of picking an idea from whatever was retrieved.", "bullet": True},
          {"text": "**Leakage-safe by construction:** every search is filtered to papers published before the "
                   "target paper.", "bullet": True}], PALE_GREEN, GREEN, body_size=13, space=8)


def funnel_slide_body(slide) -> None:
    """Slide 4's funnel: what happens to one question, in plain words, as shrinking bars."""
    textbox(slide, Inches(0.55), Inches(2.72), Inches(6.7), Inches(0.35),
            "**What happens to one question** (average over our 135 test questions)", size=13, color=NAVY, space=0)
    stages = [
        (f"{CD['search_hits']:.0f}", "papers found", "by three keyword searches", GRAY),
        (f"{CD['admitted']:.0f}", "pass the rules", "published before the cutoff, open access, a research article", GRAY),
        (f"{CD['corpus_papers']:.0f}", "papers opened in full",
         "the 50 best matches to the question, plus papers they often cite", TEAL),
        (f"{CD['corpus_passages']:,.0f}", "passages", "each paper's full text split into sections", TEAL),
        (f"{CD['pack_passages']:.0f}", "passages to the writer",
         f"those closest to the draft idea, ≈ {CD['pack_chars'] / 1000:.0f}k characters (≈ 4 pages), from "
         f"{CD['pack_papers']:.0f} papers", GREEN),
    ]
    top = max(float(st[0].replace(",", "")) for st in stages)
    y = Inches(3.12)
    for count, head, body, color in stages:
        width = Inches(0.55 + 1.65 * (float(count.replace(",", "")) / top) ** 0.5)
        rect(slide, Inches(0.55), y, width, Inches(0.55), color, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        textbox(slide, Inches(0.55), y + Inches(0.08), width, Inches(0.4), f"**{count}**", size=15, color=WHITE,
                align=PP_ALIGN.CENTER, space=0)
        textbox(slide, Inches(2.85), y + Inches(0.02), Inches(4.45), Inches(0.6),
                [{"text": f"**{head}**", "size": 12.5, "space": 0},
                 {"text": body, "size": 10.5, "color": GRAY, "space": 0}], space=0)
        y += Inches(0.72)


# ---------------------------------------------------------------- part 2: the agent, step by step

def step_slide(prs, number: int, title: str, what: list, prompt_title: str, prompt: str, example: list,
               notes: str, prompt_size: float = 9.0, left_w: float = 5.5) -> None:
    slide = new_slide(prs, f"Our agent · step {number} of 5", title, section_color=GREEN, notes=notes)
    textbox(slide, Inches(0.55), Inches(1.35), Inches(left_w), Inches(2.6),
            [{"text": "**What happens**", "size": 13, "color": GREEN, "space": 4}] +
            [{"text": w, "bullet": True, "size": 12.5, "bullet_color": GREEN, "space": 4} for w in what], space=4)
    card(slide, Inches(0.55), Inches(4.05), Inches(left_w), Inches(2.85), "Example run (the zirconium paper)",
         example, PALE_TEAL, TEAL, body_size=11.5, space=3)
    prompt_box(slide, Inches(0.55 + left_w + 0.25), Inches(1.35), Inches(12.25 - left_w - 0.25), Inches(5.55),
               prompt_title, prompt, size=prompt_size)


def agent_steps(prs) -> None:
    s0 = T["stage0_benchmark_case"]
    draft_call, writer_call = EX["calls"][0], EX["calls"][1]
    draft, final = draft_call["output"], writer_call["output"]
    srch, rank = EX["search"], EX["ranking"]
    question = EX["question"]
    demo_note = ("This step-by-step example is a fresh run of the same agent on this question (draft_example.py, "
                 "10 November); the agent's 270 stored runs did not keep the closed-book draft. All scores in the "
                 "results come from the stored runs.")
    gate = s0["question"]["checks_and_lexical_gate"]["problem_constrained"]
    step_slide(prs, 1, "The input: a research question and a knowledge cutoff", [
        "The user asks one research question; nothing else is given: no paper, no corpus, no extracted data.",
        "The knowledge cutoff is the date before which all evidence must be published (here, the hidden paper's "
        "publication date).",
        "In the benchmark the question comes from a held-out paper's introduction, with the paper's own "
        "contribution removed and leakage checked."],
        "Input to the agent (JSON)",
        json.dumps({"query": question, "knowledge_cutoff": EX["cutoff"]}, indent=1, ensure_ascii=False),
        [f"Hidden paper: “{T['paper']['title'].rstrip('.')}”, {T['paper']['publication_date']}.",
         "The question never names zirconium, the paper's intervention.",
         f"Leakage checker: {len(gate['leaks'])} leaking phrases; answer-word overlap {gate['overlap']:.1%} "
         f"(gate ≤ 10%)."],
        notes="The question is the problem-constrained level of PMC11643467 (test4). " + demo_note, prompt_size=11)
    step_slide(prs, 2, "Draft an idea first, without evidence (o3-mini, 1 call)", [
        "o3-mini reads only the question and writes a complete hypothesis from its own knowledge, before seeing any "
        "paper.",
        "This fixes the agent's own idea first, so the evidence it reads later supports and sharpens the idea "
        "instead of supplying it.",
        "The prompt is conservative: predict only as far as support allows, state uncertainty instead of inventing "
        "values."],
        "Prompt: writer (WRITER_B with the output schema, verbatim); the evidence list is empty",
        draft_call["system"],
        [f"**Draft hypothesis:** {clip(draft['hypothesis'], 220)}",
         f"**Intervention:** {clip(draft['intervention'], 160)}",
         f"**Mechanism:** {clip(draft['mechanism'], 170)}"],
        notes="loop_methods.m_agent(choose=False, ground=True): write(h, {}, 'o3mini', role='draft', "
              "system=WRITER_B); input {query, knowledge_cutoff, analysis_notes: {}, eligible_evidence: []}. "
              + demo_note, prompt_size=8.5)
    q0 = srch["searches"][0]
    step_slide(prs, 3, "Search the literature for this question (Llama-3.3 + Europe PMC)", [
        "Llama-3.3 turns the question into three short keyword phrases (1 call; the prompt is on the right).",
        "Each phrase becomes a database search: any of its words in the abstract, a high-entropy-alloy term in the "
        "title or abstract, open access, full text, no preprints, published before the cutoff.",
        "Rule checks on every paper: dated before the cutoff by two sources, a research article, not the hidden "
        "paper or a close relative.",
        "The 50 papers that best match the question's words are kept, plus papers that at least two of them cite."],
        "Prompt: keyword phrases (Llama-3.3, 1 call, verbatim)",
        srch["keyword_system"] + "\n\nOutput for this question:\n" + "\n".join(f"• {p}" for p in srch["phrases"]) +
        "\n\nThe first phrase's search, as sent to Europe PMC:\n" + q0["query"],
        [f"Hits per phrase: " + ", ".join(f"“{s['phrase']}”: {s['hit_count']}" for s in srch["searches"]) + ".",
         f"{srch['unique_hits']} distinct papers found → after the rule checks, the best 50 kept, plus "
         f"{srch['expansion']} papers they cite.",
         f"The question's corpus: {EX['pool']['papers']} papers, {EX['pool']['passages']:,} passages."],
        notes="websearch.phrases_for (Llama-3.3-70B, temperature 0, cached per question) and websearch.build_corpus "
              "(phrase_query, admit, bm25_rank on the question's and phrases' words, 50 seeds, expansion by "
              "co-citation >= 2). Built per question from searches; no model reads the papers.", prompt_size=9)
    packed = rank["packed"]
    step_slide(prs, 4, "Read the papers and rank passages against the draft (rules, no model)", [
        "Each paper's open-access full text is split by section into passages of at most 1,600 characters.",
        "All passages are ranked by word overlap (BM25) with the draft's intervention, structural mediator and "
        "mechanism, so the evidence is about the agent's own idea.",
        "The top passages are kept up to 16,000 characters (at most 24). No model reads anything in this step."],
        "Rule (code, not a prompt)",
        "search_text = draft.intervention + draft.structural_mediator\n"
        "              + draft.mechanism\n"
        "passages = split_by_section(full_text(paper), 1600)\n"
        "           for every paper in the question's corpus\n"
        "ranked = bm25(search_text, passages)    # word overlap\n"
        "pack = top of ranked, up to 16,000 characters,\n"
        "       at most 24 passages\n\n"
        "Search text in this run (from the draft):\n" + clip(rank["search_text"], 600),
        [f"{EX['pool']['passages']:,} passages ranked → {rank['pack']['records']} kept "
         f"({rank['pack']['chars']:,} characters, {rank['pack']['papers']} papers), for example:"] +
        [f"• {clip(strip_tags(p['title']), 70)} ({clip(p['section'], 28)})" for p in packed[:4]],
        notes="loop_methods.focused_pack and _pcd_ranked (BM25 over content words; records sharing no word are "
              "dropped). " + demo_note, prompt_size=10.5)
    step_slide(prs, 5, "Rewrite the hypothesis with the evidence (o3-mini, 1 call)", [
        "o3-mini receives the question, the draft's intervention as the chosen lever, and the ranked passages.",
        "The same conservative prompt tells it to build on the lever and use the evidence only as far as it "
        "supports; it cites the passages it relies on.",
        "Result: the agent's own idea, made more specific and backed by earlier work."],
        "Prompt: writer (WRITER_B with the output schema, verbatim); notes = {\"lever\": draft intervention}",
        writer_call["system"],
        [f"**Lever from the draft:** {clip(writer_call['input']['analysis_notes']['lever'], 140)}",
         f"**Final hypothesis:** {clip(final['hypothesis'], 210)}",
         f"**Intervention:** {clip(final['intervention'], 150)}",
         f"Cites {len(EX['run']['cited_ids'])} passage(s); every leakage counter zero."],
        notes="write(h, {'lever': draft intervention}, 'o3mini', records=pack, system=WRITER_B). " + demo_note,
        prompt_size=8.5)


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
    v = R["controls"]["gaps"]
    slide = new_slide(prs, "Evaluation", "Metrics: how strong is the research proposal?", section_color=NAVY, notes=(
        "Research quality (RQ): rq_judge.py, the expert package's scales verbatim (loop.md 24.1). Decision rule: "
        "pairwise preference (loop.md 27.1). Controls of this session (three calls): loop.md 27.2; re-test: loop.md "
        "24.3. The answer key is not used by any metric; it only builds and leak-checks the questions."))
    card(slide, Inches(0.55), Inches(1.4), Inches(6.1), Inches(2.6), "Research quality, RQ (0–4)", [
        {"text": "RQ = mean(plausibility, testability, usefulness) − 1", "size": 14, "font": MONO, "space": 8},
        {"text": "**Plausibility, testability, usefulness** (1–5): the materials expert's own blind scales, with "
                 "their anchors verbatim.", "bullet": True},
        {"text": "Judged by DeepSeek-V4-Pro from the question and the hypothesis only (no citations, no evidence, no "
                 "answer key); mean of 3 calls.", "bullet": True}], PALE_TEAL, TEAL, body_size=12.5, space=4)
    card(slide, Inches(6.85), Inches(1.4), Inches(5.95), Inches(2.6), "Decisions: pairwise preference", [
        {"text": "Each method's hypothesis vs the closed-book writer's, for the same question and sample.",
         "bullet": True},
        {"text": "Shown in both orders; a win needs both. Net preference per paper, 95% CI over papers.",
         "bullet": True},
        {"text": "**DeepSeek** decides during development; **GPT-5.6** is held out to confirm; **o1** alongside.",
         "bullet": True}], PALE_TEAL, TEAL, body_size=12.5, space=4)
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
    p = DI["prompts"]
    rq = p["RQ_SYSTEM"]
    cut = rq.index("Rate the hypothesis on three")
    slide = new_slide(prs, "Evaluation · prompts (verbatim)", "Research-quality judge (DeepSeek, 3 calls per hypothesis)",
                      section_color=GRAY, notes=(
                          "rq_judge.RQ_SYSTEM: the expert package's instructions and scales, verbatim (loop.md 24.1). "
                          "Input: {research_question, hypothesis rendered as the expert sees it}; no citations, no "
                          "evidence, no answer key."))
    # One prompt, laid out in two columns inside a single box because it is too long for one column.
    rect(slide, Inches(0.55), Inches(1.35), Inches(12.25), Inches(5.6), LIGHT, line=RGB_LINE,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    textbox(slide, Inches(0.67), Inches(1.43), Inches(12.0), Inches(0.3),
            "The research-quality judge's prompt (one prompt, one judge: DeepSeek), shown in two columns",
            size=11.5, color=TEAL, space=0).text_frame.paragraphs[0].runs[0].font.bold = True
    for x, part in ((0.67, rq[:cut].rstrip()), (6.8, rq[cut:])):
        textbox(slide, Inches(x), Inches(1.78), Inches(5.9), Inches(5.1),
                [{"text": line or " ", "size": 8.5, "font": MONO, "space": 0} for line in part.split("\n")], space=0)
    line = slide.shapes.add_connector(1, Inches(6.68), Inches(1.8), Inches(6.68), Inches(6.8))
    line.line.color.rgb = RGB_LINE
    slide = new_slide(prs, "Evaluation · prompts (verbatim)", "Pairwise judge (DeepSeek · GPT-5.6 · o1, both orders)",
                      section_color=GRAY, notes=(
                          "diag_analysis.QUALITY_PAIR_SYSTEM, verbatim as it was run. Input: the question and two "
                          "candidates, each with the passages it cites (neutral labels); run in both orders."))
    prompt_box(slide, Inches(0.55), Inches(1.35), Inches(7.6), Inches(4.0), "Pairwise judge prompt",
               p["QUALITY_PAIR_SYSTEM"], size=11)
    card(slide, Inches(8.4), Inches(1.35), Inches(4.4), Inches(4.0), "Input to the judge", [
        {"text": "The research question.", "bullet": True},
        {"text": "Candidate A and candidate B: each hypothesis with the passages it cites (neutral labels).",
         "bullet": True},
        {"text": "Every pair is judged twice, with A and B swapped; a win needs both.", "bullet": True},
        {"text": "No answer key, no method names.", "bullet": True}], PALE_TEAL, TEAL, body_size=13, space=6)


def c(x: dict) -> str:
    if not x or not x.get("papers"):
        return "–"
    return f"{x['diff']:+.2f} ({x['up']} vs {x['down']})"


def results_slides(prs) -> None:
    rows_data = R["rows"]
    order = [("agent_draft_ground_b_o3mini", "**Our agent: draft, then read on demand and rewrite**"),
             ("rx_r", "Read on demand first, then write (no draft)"),
             ("rx_base", "Unscreened per-question web corpus + writer"),
             ("agent_choose_ground_b_o3mini", "Agent that picks a lever, then retrieves evidence"),
             ("rx_ruc", "Read on demand + a multi-critic refinement loop"),
             ("writer_only_b_o3mini", "Closed-book writer (no retrieval)"),
             ("closed_book", "Llama-3.3 baseline")]
    slide = new_slide(prs, "Results", "Results: highest research quality, and preferred over the closed-book writer",
                      section_color=GREEN, notes=(
                          "loop_quality/analysis_quality.md (experiment 46; loop.md 27.4); stored scores of the "
                          "agent's 270 runs. RQ: DeepSeek, mean of 3 calls. Pairwise: net preference per paper over "
                          "the closed-book writer, both orders must agree; in brackets: papers in which each side is "
                          "preferred (out of 45). GPT-5.6 was run only for the top three by DeepSeek preference, "
                          "which did not include our agent. 50 methods scored, 20 compared head-to-head; 7 shown."))
    rows = [["Method", "RQ", "Plaus.", "Test.", "Useful.", "Pairwise vs closed-book: DeepSeek", "o1", "GPT-5.6"]]
    fills = [None]
    for m, label in order:
        x = rows_data[m]
        s = x["scales"]
        p = x["pairwise"]
        ref = m == "writer_only_b_o3mini"
        rows.append([label, f"{x['rq']:.2f}", f"{s['plausibility']:.2f}", f"{s['testability']:.2f}",
                     f"{s['usefulness']:.2f}", "(reference)" if ref else c(p.get("deepseek")),
                     "" if ref else c(p.get("o1")), "" if ref else (c(p["gpt56"]) if (p.get("gpt56") or {}).get("papers") else "not run")])
        fills.append(PALE_GREEN if m == "agent_draft_ground_b_o3mini" else None)
    ref = R["references"]["oracle_hint_full_b_o3mini"]
    rows.append(["Reference: the authors' own study, written as a proposal", f"{ref['rq']:.2f}", "", "", "",
                 c(ref["pairwise"].get("deepseek")), "", ""])
    fills.append(PALE_AMBER)
    table(slide, Inches(0.55), Inches(1.35), Inches(12.25), rows, [4.3, 0.75, 0.8, 0.75, 0.85, 2.3, 1.25, 1.25],
          size=10.5, row_height=0.45, fills=fills)
    textbox(slide, Inches(0.55), Inches(6.0), Inches(12.25), Inches(0.9),
            "RQ on 0–4; the three scales on 1–5. 45 papers, 135 questions, 270 hypotheses per method. Pairwise in "
            "brackets: papers in which each side is preferred. The closed-book writer's RQ drifts between judging "
            "sessions (3.10 here, 3.15 when re-judged alongside our agent); paired comparisons use the same session.",
            size=11, color=GRAY)

    x = rows_data["agent_draft_ground_b_o3mini"]
    p = x["pairwise"]
    slide = new_slide(prs, "Results", "What the results say", section_color=GREEN, notes=(
        "Paired over the 45 papers, 95% CI. Against rx_r (read first, then write): RQ +0.12 [+0.02, +0.23], "
        "plausibility +0.15 [+0.02, +0.29], testability +0.07 [0.00, +0.15], usefulness +0.14 [0.00, +0.29]. Against "
        "the closed-book writer judged in the same session: RQ +0.01 [-0.06, +0.07]. RQ of the 45 o3-mini "
        "configurations: 2.81-3.16; our agent 3.156 and a four-draft synthesis method 3.157 are the two highest. "
        "Pairwise vs the writer: our agent DeepSeek +0.27, o1 +0.33; rx_r +0.50, +0.59 (GPT-5.6 +0.54)."))
    base.bar_chart(slide, Inches(0.45), Inches(1.35), Inches(6.3), Inches(3.0), "Our agent's three scales (1–5)",
                   ["Usefulness", "Testability", "Plausibility"],
                   [x["scales"]["usefulness"], x["scales"]["testability"], x["scales"]["plausibility"]],
                   [GREEN, GREEN, AMBER], maximum=5.0, cat_size=12)
    textbox(slide, Inches(0.55), Inches(4.6), Inches(6.2), Inches(2.3), [
        {"text": "**Preferred over the closed-book writer by both judges run**", "size": 13.5, "space": 4},
        {"text": f"DeepSeek {p['deepseek']['diff']:+.2f}: {p['deepseek']['up']} papers vs {p['deepseek']['down']}",
         "bullet": True, "size": 12.5},
        {"text": f"o1 {p['o1']['diff']:+.2f}: {p['o1']['up']} vs {p['o1']['down']}", "bullet": True, "size": 12.5},
        {"text": "GPT-5.6 (held-out judge): not yet run for this agent", "bullet": True, "size": 12.5,
         "color": GRAY}], space=3)
    card(slide, Inches(7.0), Inches(1.4), Inches(5.8), Inches(5.5), "Findings", [
        {"text": f"**Highest research quality of the 50 methods** (RQ {x['rq']:.2f}, tied with one other).",
         "bullet": True},
        {"text": "**Drafting first helps**: against reading first and then writing, RQ +0.12 [+0.02, +0.23] and "
                 "plausibility +0.15 [+0.02, +0.29].", "bullet": True},
        {"text": "**Head-to-head, both judges prefer it** to the closed-book writer (39 papers vs 1).",
         "bullet": True},
        {"text": "**No extraction corpus was needed** at any point; three model calls per question.",
         "bullet": True},
        {"text": "**On RQ alone it ties the closed-book writer** (+0.01 in the same session): the scales sit near "
                 "their ceiling.", "bullet": True, "bullet_color": AMBER},
        {"text": "**Reading first, then writing is preferred more often head-to-head** (+0.50 vs +0.27), with "
                 "lower RQ: the two measures disagree.", "bullet": True, "bullet_color": AMBER},
        {"text": "**Caveat**: AI judges, which prefer the AI proposals to the authors' own studies; the expert's "
                 "blind ratings must confirm.", "bullet": True, "bullet_color": RED}],
         PALE_GREEN, GREEN, body_size=12, space=5)


def closing_slide(prs) -> None:
    slide = new_slide(prs, "Summary", "Summary and next steps", section_color=TEAL, notes=(
        "Next steps follow loop.md 27.1 (phases 2-4) and 27.7."))
    card(slide, Inches(0.55), Inches(1.4), Inches(6.0), Inches(5.0), "Summary", [
        {"text": "Extract-first pipelines pay a corpus-sized extraction cost up front, and again as the literature "
                 "grows.", "bullet": True},
        {"text": f"Our agent extracts nothing in advance: per question it drafts an idea, searches, opens "
                 f"~{CD['corpus_papers']:.0f} full texts and reads the ~{CD['pack_passages']:.0f} passages closest "
                 f"to its draft, then rewrites.", "bullet": True},
        {"text": "It has the highest research quality of the 50 methods, and both judges run prefer it to the "
                 "closed-book writer.", "bullet": True}], PALE_TEAL, TEAL, body_size=15, space=10)
    card(slide, Inches(6.8), Inches(1.4), Inches(6.0), Inches(5.0), "Next steps", [
        {"text": "**Held-out judge**: run GPT-5.6 pairwise for our agent.", "bullet": True},
        {"text": "**Plausibility**: the weakest scale (3.72 of 5); target it next.", "bullet": True},
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
