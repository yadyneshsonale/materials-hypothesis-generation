"""Build the 2026-11-04 status deck: what has been run, where it fails, where it excels, and one real run end to end
with every prompt. Reads example_trace.json (made by make_example_trace.py); headline numbers are from the records
cited in each slide's notes. Needs python-pptx (not a project dependency):

    python3 -m venv /tmp/pptx_env && /tmp/pptx_env/bin/pip install python-pptx
    /tmp/pptx_env/bin/python presentations/2026-11-04_status/build_deck.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
T = json.loads((HERE / "example_trace.json").read_text())
OUT = HERE / "hypothesis_generation_status_2026-11-04.pptx"

NAVY, TEAL, GREEN, RED, AMBER = (RGBColor(0x1B, 0x2A, 0x41), RGBColor(0x0F, 0x76, 0x6E), RGBColor(0x15, 0x80, 0x3D),
                                 RGBColor(0xB9, 0x1C, 0x1C), RGBColor(0xB4, 0x53, 0x09))
TEXT, GRAY, LIGHT, WHITE = RGBColor(0x1F, 0x29, 0x37), RGBColor(0x5B, 0x65, 0x73), RGBColor(0xF1, 0xF5, 0xF9), \
    RGBColor(0xFF, 0xFF, 0xFF)
PALE_GREEN, PALE_RED, PALE_TEAL, PALE_AMBER = (RGBColor(0xEC, 0xFD, 0xF3), RGBColor(0xFE, 0xF2, 0xF2),
                                               RGBColor(0xE6, 0xF4, 0xF2), RGBColor(0xFF, 0xF7, 0xED))
SANS, MONO = "Calibri", "Consolas"
W, H = Inches(13.333), Inches(7.5)
FOOTER = "AI hypothesis generation for high-temperature HEAs · status 4 Nov 2026"


# ---------------------------------------------------------------- helpers

def rich(paragraph, text: str, size: float, color: RGBColor = TEXT, font: str = SANS, bold: bool = False) -> None:
    """Add runs to a paragraph; **...** marks bold."""
    for n, part in enumerate(re.split(r"\*\*", text)):
        if not part:
            continue
        run = paragraph.add_run()
        run.text = part
        run.font.size, run.font.name, run.font.color.rgb = Pt(size), font, color
        run.font.bold = bold or n % 2 == 1


def bullet(paragraph, level: int = 0, char: str = "•", color: RGBColor = TEAL) -> None:
    ppr = paragraph._p.get_or_add_pPr()
    indent = Inches(0.22)
    ppr.set("marL", str(int(indent * (level + 1) + Inches(0.05) * level)))
    ppr.set("indent", str(-int(indent)))
    clr = etree.SubElement(ppr, qn("a:buClr"))
    etree.SubElement(clr, qn("a:srgbClr")).set("val", str(color))
    etree.SubElement(ppr, qn("a:buFont")).set("typeface", "Arial")
    etree.SubElement(ppr, qn("a:buChar")).set("char", char)


def textbox(slide, x, y, w, h, items, size: float = 15, color: RGBColor = TEXT, font: str = SANS,
            space: float = 6, anchor=MSO_ANCHOR.TOP, align=PP_ALIGN.LEFT, margins: float = 0.05):
    """items: a string, or a list of strings / (text, level) / dict(text, level, size, color, bold, bullet)."""
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(margins)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    items = [items] if isinstance(items, str) else items
    for n, item in enumerate(items):
        spec = item if isinstance(item, dict) else ({"text": item[0], "level": item[1], "bullet": True}
                                                     if isinstance(item, tuple) else {"text": item})
        p = tf.paragraphs[0] if n == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(spec.get("space", space))
        if spec.get("bullet"):
            bullet(p, spec.get("level", 0), color=spec.get("bullet_color", TEAL))
        rich(p, spec["text"], spec.get("size", size), spec.get("color", color), spec.get("font", font),
             spec.get("bold", False))
    return box


def rect(slide, x, y, w, h, fill: RGBColor, line: RGBColor | None = None, shape=MSO_SHAPE.RECTANGLE):
    s = slide.shapes.add_shape(shape, x, y, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1)
    s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.08
    return s


def card(slide, x, y, w, h, title: str, body, fill: RGBColor, accent: RGBColor, title_size: float = 15,
         body_size: float = 13, space: float = 5):
    rect(slide, x, y, w, h, fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(slide, x, y + Inches(0.12), Inches(0.07), h - Inches(0.24), accent)
    textbox(slide, x + Inches(0.18), y + Inches(0.08), w - Inches(0.28), Inches(0.42), title, size=title_size,
            color=accent, space=0).text_frame.paragraphs[0].runs[0].font.bold = True
    return textbox(slide, x + Inches(0.18), y + Inches(0.5), w - Inches(0.3), h - Inches(0.58), body,
                   size=body_size, space=space)


def arrow(slide, x, y, w, h, color: RGBColor = GRAY):
    s = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x, y, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = color
    s.line.fill.background()
    s.shadow.inherit = False


def table(slide, x, y, w, rows: list[list[str]], widths: list[float], size: float = 11, header_fill=NAVY,
          row_height: float = 0.3, fills: list[RGBColor | None] | None = None, bold_first_col: bool = False,
          col_colors: dict[int, RGBColor] | None = None, header_height: float = 0.4):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), x, y, w,
                                   Inches(header_height + row_height * (len(rows) - 1)))
    tbl = shape.table
    tbl.first_row = True
    for c, width in enumerate(widths):
        tbl.columns[c].width = Inches(width)
    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(header_height if r == 0 else row_height)
        for c, value in enumerate(row):
            cell = tbl.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.06)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if r == 0:
                cell.fill.fore_color.rgb = header_fill
            else:
                fill = (fills or [None] * len(rows))[r] if fills else None
                cell.fill.fore_color.rgb = fill or (LIGHT if r % 2 == 0 else WHITE)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            color = WHITE if r == 0 else (col_colors or {}).get(c, TEXT)
            rich(p, value, size, color, bold=(r == 0 or (bold_first_col and c == 0)))
    return tbl


def bar_chart(slide, x, y, w, h, title: str, categories: list[str], values: list[float], colors: list[RGBColor],
              maximum: float = 4.0, label_size: float = 12, cat_size: float = 12, fmt: str = "0.00"):
    data = CategoryChartData()
    data.categories = categories
    data.add_series(title, values)
    chart = slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, x, y, w, h, data).chart
    chart.has_legend = False
    chart.has_title = True
    chart.chart_title.text_frame.text = title
    run = chart.chart_title.text_frame.paragraphs[0].runs[0]
    run.font.size, run.font.bold, run.font.color.rgb, run.font.name = Pt(13), True, NAVY, SANS
    plot = chart.plots[0]
    plot.gap_width = 55
    plot.has_data_labels = True
    labels = plot.data_labels
    labels.number_format, labels.number_format_is_linked = fmt, False
    labels.position = XL_LABEL_POSITION.OUTSIDE_END
    labels.font.size, labels.font.bold, labels.font.name = Pt(label_size), True, SANS
    for point, color in zip(plot.series[0].points, colors):
        point.format.fill.solid()
        point.format.fill.fore_color.rgb = color
    va = chart.value_axis
    va.minimum_scale, va.maximum_scale = 0, maximum
    va.has_major_gridlines = False
    va.visible = False
    ca = chart.category_axis
    ca.reverse_order = True
    ca.tick_labels.font.size, ca.tick_labels.font.name = Pt(cat_size), SANS
    ca.format.line.color.rgb = GRAY
    return chart


def new_slide(prs, section: str, title: str, notes: str = "", section_color: RGBColor = TEAL):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    rect(slide, 0, 0, W, Inches(0.09), section_color)
    textbox(slide, Inches(0.55), Inches(0.22), Inches(9), Inches(0.3), section.upper(), size=11,
            color=section_color, space=0).text_frame.paragraphs[0].runs[0].font.bold = True
    textbox(slide, Inches(0.55), Inches(0.48), Inches(12.3), Inches(0.7), title, size=27, color=NAVY, space=0
            ).text_frame.paragraphs[0].runs[0].font.bold = True
    textbox(slide, Inches(0.55), Inches(7.08), Inches(9), Inches(0.3), FOOTER, size=9, color=GRAY, space=0)
    number = len(prs.slides)
    textbox(slide, Inches(12.0), Inches(7.08), Inches(0.8), Inches(0.3), str(number), size=9, color=GRAY, space=0,
            align=PP_ALIGN.RIGHT)
    if notes:
        slide.notes_slide.notes_text_frame.text = notes
    return slide


def clip(text: str, n: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + " …"


# ---------------------------------------------------------------- part 1: status

def title_slide(prs) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    rect(slide, 0, 0, W, H, NAVY)
    rect(slide, Inches(0.8), Inches(2.0), Inches(0.12), Inches(2.3), TEAL)
    textbox(slide, Inches(1.15), Inches(1.85), Inches(11.2), Inches(1.6),
            "AI hypothesis generation for high-temperature high-entropy alloys", size=40, color=WHITE, space=0
            ).text_frame.paragraphs[0].runs[0].font.bold = True
    textbox(slide, Inches(1.15), Inches(3.45), Inches(11.2), Inches(0.9),
            "What has been run · where it fails · where it excels · one real run, end to end, with every prompt",
            size=20, color=RGBColor(0xCB, 0xD5, 0xE1), space=0)
    textbox(slide, Inches(1.15), Inches(5.6), Inches(11), Inches(0.9),
            ["Status after 45 experiments · 4 November 2026",
             "Repository: materials-hypothesis-generation · details in PROJECT_SUMMARY.md and loop.md"],
            size=14, color=RGBColor(0x94, 0xA3, 0xB8), space=4)
    slide.notes_slide.notes_text_frame.text = (
        "Part 1 (slides 2-7): status. Part 2 (slides 8-14): one real run with every intermediate output and the "
        "judges' inputs and outputs. Appendix (slides 15-19): every prompt, verbatim. The complete trace is in "
        "presentations/2026-11-04_status/example_trace.md.")


def task_slide(prs) -> None:
    slide = new_slide(prs, "Status", "The task, and how it is scored", notes=(
        "Benchmark: 45 held-out papers (36 in the v3.1 sets and 9 in test4), 3 question levels each. Only models "
        "whose training cutoff precedes the paper see a question (must_obey.md section 2). Scores: section 2 of "
        "PROJECT_SUMMARY.md; RQ: loop.md 24.1."))
    steps = [("1  Real paper", "45 open-access papers on high-temperature HEAs, newer than the models"),
             ("2  Research question", "written from the paper's introduction with its own work removed; "
                                      "leakage-checked; 3 levels of detail"),
             ("3  Agent", "pre-cutoff models only (o3-mini writes); literature dated before the paper"),
             ("4  Hypothesis", "intervention, conditions, structure, mechanism, predicted outcome, baseline, "
                               "falsifying test"),
             ("5  Judges", "GPT-5.6 (primary) and DeepSeek compare it with the paper's hidden answer key")]
    x0, y0, bw, bh, gap = Inches(0.55), Inches(1.45), Inches(2.25), Inches(2.25), Inches(0.27)
    for n, (head, body) in enumerate(steps):
        x = x0 + n * (bw + gap)
        rect(slide, x, y0, bw, bh, PALE_TEAL if n != 4 else PALE_AMBER, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        textbox(slide, x + Inches(0.12), y0 + Inches(0.12), bw - Inches(0.24), Inches(0.45), f"**{head}**", size=15,
                color=NAVY, space=0)
        textbox(slide, x + Inches(0.12), y0 + Inches(0.62), bw - Inches(0.24), bh - Inches(0.7), body, size=13,
                space=0)
        if n < 4:
            arrow(slide, x + bw + Inches(0.03), y0 + bh / 2 - Inches(0.11), gap - Inches(0.06), Inches(0.22))
    card(slide, Inches(0.55), Inches(4.0), Inches(6.0), Inches(2.25), "Reconstruction score (0–4): the main metric",
         ["Mean agreement with the paper on **intervention, conditions, mechanism and outcome**.",
          "Asks: did the agent propose what the authors actually did?"], PALE_AMBER, AMBER, body_size=14)
    card(slide, Inches(6.8), Inches(4.0), Inches(6.0), Inches(2.25), "Research quality, RQ (0–4)",
         ["**Plausibility, testability, usefulness** on the expert's own 1–5 scales, minus 1; judged **without** "
          "the answer key.", "Asks: is it a good research proposal?"], PALE_TEAL, TEAL, body_size=14)
    textbox(slide, Inches(0.55), Inches(6.45), Inches(12.2), Inches(0.5),
            "135 questions (45 papers × 3 levels) · 2 samples each · paired statistics with paper-clustered 95% CIs · "
            "every experiment pre-registered", size=12, color=GRAY)


def run_slide(prs) -> None:
    slide = new_slide(prs, "Status", "What has been run: 45 experiments, about 34,000 hypotheses", notes=(
        "Sources: PROJECT_SUMMARY.md section 1 and the experiment log (EXPERIMENT_LOG_2026-10-22.md). Counts: "
        "34,006 run files in 213 run configurations; 32,721 GPT-5.6 and 33,646 DeepSeek judgments (counted "
        "2026-11-04). Experiment 44 is interim: 565 of its GPT-5.6 judgments and the audits were paused on 2 Nov."))
    rows = [["Experiments", "What was tried", "What we learned"],
            ["**1–23** · Benchmark", "Top-cited open-access corpus; questions and hidden answer keys; evidence "
                                     "extraction pipelines",
             "The first benchmark leaked answers (47% of answer words in questions; a model newer than the papers). "
             "Fixing it cut scores from ~1.5 to ~0.5"],
            ["**9–35** · Methods", "Evidence pipelines (cards, rubrics, knowledge graph, citation graphs); critics, "
                                   "tournaments, verifiers, consensus; stronger models, few-shot, routers",
             "The simplest method wins: o3-mini with a conservative prompt, +0.11 over the Llama baseline on 37 "
             "fresh papers"],
            ["**36–40** · Web and agents", "Date-filtered web search for every method; propose–critique–decide "
                                           "agents; multi-model synthesis; oracle diagnostics",
             "Evidence ties the writer on the score, but blind judges prefer it"],
            ["**41–43** · Failure analysis", "Failure-point prompts; six independent stage reviews; ceiling "
                                             "analysis; research-quality score",
             "The score is capped by one paper's specific choice; hypothesis quality is high"],
            ["**44–45** · Latest", "Focused retrieval; multi-critic refinement loop with re-retrieval; "
                                   "lever-preserving editor; domain context",
             "Retrieval fixed (36% → 100% relevant); critique loop −0.15; editing ±0.01"]]
    table(slide, Inches(0.55), Inches(1.4), Inches(12.25), rows, [2.3, 5.2, 4.75], size=12.5, row_height=0.82)
    textbox(slide, Inches(0.55), Inches(6.45), Inches(12.2), Inches(0.5),
            "≈34,000 hypothesis runs · 200+ configurations · ≈32,700 GPT-5.6 and ≈33,600 DeepSeek judgments · "
            "every run checked for leakage", size=13, color=TEAL)


def excels_slide(prs) -> None:
    slide = new_slide(prs, "Status", "What it excels at", section_color=GREEN, notes=(
        "RQ: loop.md 24.3 (mean of three DeepSeek calls; re-test rho 0.82, internally validated post hoc; the "
        "authors' study is the answer key rewritten as a proposal by the same writer). Fresh papers: PROJECT_SUMMARY "
        "section 1 (+0.11 [+0.06, +0.17], 26 up / 8 down, p = 0.003; DeepSeek +0.27). Blind preference: experiment "
        "39 (o1) and experiment 44 (DeepSeek pairwise +0.16, 26/5 papers). Retrieval: loop.md 25.2. Shortlists: "
        "loop.md 26.4 (hit@10 with intervention >= 1). Leakage: loop.md 25.2 and 26.3."))
    items = [
        {"text": "**Writes strong research proposals.** Research quality 3.10 / 4: above the authors' own studies "
                 "written as proposals (2.71) and far above the Llama baseline (1.40).", "bullet": True,
         "bullet_color": GREEN},
        {"text": "AI-judged on the expert's scales (three DeepSeek calls, re-test ρ 0.82); the expert's 60 blind "
                 "ratings will confirm or correct it.", "bullet": True, "level": 1, "size": 12, "color": GRAY,
         "bullet_color": GRAY},
        {"text": "**Beats the baseline on unseen papers.** +0.11 (GPT-5.6) / +0.27 (DeepSeek) over Llama-3.3 on "
                 "37 fresh papers; better on 26, worse on 8 (p = 0.003).", "bullet": True, "bullet_color": GREEN},
        {"text": "**Uses relevant literature well.** Blind judges prefer evidence-based hypotheses (o1: 41 of 45 "
                 "papers); focused retrieval preferred in 26 vs 5 papers.", "bullet": True, "bullet_color": GREEN},
        {"text": "**Retrieval is on-topic.** Relevant papers 36% → 100%; 85% of passages graded fully relevant.",
         "bullet": True, "bullet_color": GREEN},
        {"text": "**Usually in the right area.** A related intervention appears in 54–78% of 10-idea shortlists.",
         "bullet": True, "bullet_color": GREEN},
        {"text": "**Trustworthy evaluation.** Pre-registered, two judges, blinded; every retrieved record re-dated: "
                 "0 leaks.", "bullet": True, "bullet_color": GREEN}]
    textbox(slide, Inches(0.55), Inches(1.4), Inches(7.3), Inches(5.5), items, size=15, space=9)
    bar_chart(slide, Inches(8.1), Inches(1.5), Inches(4.75), Inches(3.6), "Research quality (RQ, 0–4)",
              ["Llama-3.3 baseline", "Authors' study, as a proposal", "Our writer (o3-mini)"], [1.40, 2.71, 3.10],
              [GRAY, AMBER, GREEN], cat_size=11)
    textbox(slide, Inches(8.1), Inches(5.25), Inches(4.75), Inches(1.4),
            "Same 45 papers; DeepSeek, mean of three calls. No length effect (ρ between −0.10 and +0.10 with "
            "word count).", size=11, color=GRAY)


def fails_slide(prs) -> None:
    slide = new_slide(prs, "Status", "What it fails at", section_color=RED, notes=(
        "Reconstruction and dimensions: experiment 45 final (rx_base, GPT-5.6, 270 runs: 0.623; intervention 0.28, "
        "conditions 0.64, mechanism 0.69, outcome 0.88). Exact facts: checklist judge, experiments 33 and 35. "
        "Lever statistics: experiment 41 (writer lever >= 2: 18.9%; 11.9% of earlier papers), loop.md 26.4 (pool of "
        "15,600). Methods: experiments 14-45; best +0.03 = focused retrieval (DeepSeek; GPT-5.6 +0.00), worst -0.23 = "
        "critique loop with focused retrieval and the literature map (DeepSeek). Blind spots: experiment 41. Critic "
        "agreement: experiment 44."))
    items = [
        {"text": "**Reproducing the paper's actual study.** Reconstruction ≈ 0.62 / 4. The intervention carries "
                 "most of the lost points (0.28 / 4); exact facts of the paper are matched only 6–15% of the time.",
         "bullet": True, "bullet_color": RED},
        {"text": "**Finding the paper's specific lever.** The model's own pick matches it ~19% of the time; ~12% of "
                 "earlier papers mention it; even 116 hypotheses per question from 79 methods contain a close "
                 "match for only 26–33% of questions.", "bullet": True, "bullet_color": RED},
        {"text": "**Turning more effort into a higher score.** Evidence, knowledge graphs, critics, multi-agent "
                 "debate, critique loops, selection over 15,600 hypotheses, targeted prompts, editing: all tie or "
                 "lose (best +0.03, worst −0.23).", "bullet": True, "bullet_color": RED},
        {"text": "**Blind spots.** Processing-route studies (2% lever match) and simulation studies (0%).",
         "bullet": True, "bullet_color": RED},
        {"text": "**Judges not yet calibrated.** No expert ratings yet; critic models agree weakly (ρ 0.29–0.43); "
                 "pairwise judges show position bias.", "bullet": True, "bullet_color": RED},
        {"text": "**Throughput.** GPT-5.6 refuses ~50% of calls under shared load; 565 judgments and 2,782 audits "
                 "are paused.", "bullet": True, "bullet_color": RED}]
    textbox(slide, Inches(0.55), Inches(1.4), Inches(7.3), Inches(5.5), items, size=15, space=9)
    bar_chart(slide, Inches(8.1), Inches(1.5), Inches(4.75), Inches(3.6), "Agreement with the paper (GPT-5.6, 0–4)",
              ["Intervention", "Conditions", "Mechanism", "Outcome"], [0.28, 0.64, 0.69, 0.88],
              [RED, AMBER, AMBER, AMBER], cat_size=12)
    textbox(slide, Inches(8.1), Inches(5.25), Inches(4.75), Inches(1.4),
            "Current agent (web evidence + o3-mini writer), 270 runs. A score of 4 means the paper's own "
            "study; the paper's study rewritten as a proposal scores 3.8.", size=11, color=GRAY)


def why_slide(prs) -> None:
    slide = new_slide(prs, "Status", "Why the score is capped: it rewards one paper's specific choice", notes=(
        "Ladder: loop.md 24.1, GPT-5.6 (DeepSeek: 0.57, 0.66, 0.70, 1.50, 3.64). Shortlists: loop.md 26.4, intervention "
        ">= 2 (substantial match), random draws from each question's pool of about 116 judged hypotheses. Example: "
        "part 2 of this deck."))
    bar_chart(slide, Inches(0.45), Inches(1.35), Inches(7.2), Inches(4.3), "What the writer is told → GPT-5.6 score",
              ["Nothing extra (the agent)", "The paper's type of study", "Evidence picked with the answer key",
               "The paper's exact intervention (≤ 20 words)", "The whole answer key"], [0.62, 0.66, 0.74, 1.26, 3.38],
              [TEAL, GRAY, GRAY, AMBER, NAVY], cat_size=12)
    card(slide, Inches(7.95), Inches(1.4), Inches(4.85), Inches(1.75), "Knowing the lever is not enough",
         "Told exactly what the authors did, the writer still scores 1.26. The other points are the paper's own "
         "numbers and results, which exist only after its experiment.", PALE_AMBER, AMBER, body_size=13)
    card(slide, Inches(7.95), Inches(3.3), Inches(4.85), Inches(1.75), "More ideas do not find it",
         "A close match is among 1 idea for 3% of questions, among 10 for ~10%, among all ~116 for 26–33%.",
         PALE_RED, RED, body_size=13)
    card(slide, Inches(7.95), Inches(5.2), Inches(4.85), Inches(1.65), "The real example (part 2)",
         "Agent: Y + Hf micro-additions. Paper: Zr (Hf's chemical twin). Intervention 0 / 4; none of the 46 "
         "retrieved passages mentions Zr.", PALE_TEAL, TEAL, body_size=13)
    textbox(slide, Inches(0.55), Inches(5.85), Inches(7.1), Inches(1.0),
            "Any leakage-free method would need the paper's specific choice, which no earlier source carries. A "
            "score near 2.5 on this metric would point to leakage, not skill.", size=13, color=GRAY)


def next_slide(prs) -> None:
    slide = new_slide(prs, "Status", "Where this leaves us", notes=(
        "Fair score: proposed in loop.md 26.4 (credit agreement in kind, no credit for what the question states); "
        "it changes what the benchmark measures and needs the expert's ratings to validate. Forecaster: loop.md "
        "24.1 (methods review; chronological gate before any GPU time). Resume command: loop.md 26.5."))
    card(slide, Inches(0.55), Inches(1.45), Inches(5.6), Inches(4.75), "Conclusions",
         [{"text": "The agent writes **good, testable proposals** grounded in relevant literature.", "bullet": True},
          {"text": "The reconstruction score is at its **leakage-free ceiling (~0.62)** with these models: it needs "
                   "the paper's own choice, which no earlier source carries.", "bullet": True},
          {"text": "More prompt or agent tuning will not move this score; 45 experiments agree.", "bullet": True},
          {"text": "The open question is **measurement**: do the AI judges agree with a materials expert?",
           "bullet": True}], PALE_TEAL, TEAL, body_size=16.5, space=12)
    textbox(slide, Inches(0.55), Inches(6.4), Inches(12.25), Inches(0.5),
            "Every number in this deck comes from the project records: PROJECT_SUMMARY.md, loop.md and the experiment "
            "log; the speaker notes cite the section.", size=12, color=GRAY)
    card(slide, Inches(6.4), Inches(1.45), Inches(6.4), Inches(4.75), "Next steps",
         [{"text": "**1. Expert ratings.** Collect the 60 blind ratings: they calibrate the AI judges and confirm "
                   "or correct RQ 3.10.", "space": 10},
          {"text": "**2. A fair score (recommended).** Credit the right kind of study, the property and its "
                   "direction, the regime and the mechanism; ignore numbers only the paper could know; validate "
                   "against the expert.", "space": 10},
          {"text": "**3. Optional: a next-study forecaster** trained on 1,122 earlier problem → study pairs "
                   "(25–60 GPU-hours; expected 0.65–0.85).", "space": 10},
          {"text": "**4. Housekeeping.** Resume the paused GPT-5.6 work to finalise experiment 44; any new claim "
                   "needs a fresh test set (test5).", "space": 10}], PALE_AMBER, AMBER, body_size=16)


# ---------------------------------------------------------------- part 2: the real example

def example_input_slide(prs) -> None:
    q0 = T["stage0_benchmark_case"]["question"]
    gate = q0["checks_and_lexical_gate"]["problem_constrained"]
    slide = new_slide(prs, "Real example · 1/7", "The user input and the pipeline", notes=(
        f"Run {T['run_id']} (focused retrieval + WRITER_B, o3-mini), chosen as typical: its GPT-5.6 score is the most "
        "common value (0.75; mean 0.625), its evidence pack is typical (46 passages; median 46), and its paper has no "
        "date caveats. Complete inputs and outputs: example_trace.md / example_trace.json in this folder."))
    textbox(slide, Inches(0.55), Inches(1.35), Inches(12.3), Inches(0.62),
            f"**Hidden paper** (never shown to the agent): “{T['paper']['title'].rstrip('.')}” · published "
            f"{T['paper']['publication_date']} · held-out set test4 · doi {T['paper']['doi']}", size=13, color=GRAY)
    rect(slide, Inches(0.55), Inches(2.0), Inches(12.25), Inches(1.75), PALE_TEAL, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(slide, Inches(0.55), Inches(2.12), Inches(0.07), Inches(1.51), TEAL)
    textbox(slide, Inches(0.8), Inches(2.08), Inches(11.9), Inches(1.65),
            [{"text": "USER INPUT (question, problem-constrained level)", "size": 11, "color": TEAL, "bold": True,
              "space": 3},
             {"text": f"“{T['user_input']['question']}”", "size": 14.5}], space=0)
    textbox(slide, Inches(0.55), Inches(3.88), Inches(12.3), Inches(0.75),
            [f"**Knowledge cutoff** {T['user_input']['knowledge_cutoff']}: every paper the agent sees is dated "
             "2024-11-30 or earlier (Europe PMC: open access, full text, no preprints).",
             f"**How the question was made:** GPT-5.6 wrote it from the paper's introduction with the paper's own "
             f"contribution removed; a separate checker found {len(gate['leaks'])} leaking phrases; answer-word "
             f"overlap {gate['overlap']:.1%} (gate ≤ 10%); passed in round {q0['rounds']}."], size=12.5, space=3)
    steps = [("1 Plan searches", "o3-mini"), ("2 Search", "Europe PMC + earlier corpus"), ("3 Screen papers", "gpt-4o"),
             ("4 Grade passages", "gpt-4o"), ("5 Write hypothesis", "o3-mini"), ("6 Score vs answer key", "GPT-5.6, DeepSeek"),
             ("7 Quality, no key", "DeepSeek ×3, pairwise")]
    x0, y0, bw, bh, gap = Inches(0.55), Inches(4.95), Inches(1.56), Inches(1.05), Inches(0.225)
    for n, (head, model) in enumerate(steps):
        x = x0 + n * (bw + gap)
        fill = PALE_AMBER if n >= 5 else LIGHT
        rect(slide, x, y0, bw, bh, fill, line=TEAL if n < 5 else AMBER, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        textbox(slide, x + Inches(0.06), y0 + Inches(0.08), bw - Inches(0.12), bh - Inches(0.12),
                [{"text": f"**{head}**", "size": 12, "color": NAVY, "space": 2},
                 {"text": model, "size": 10.5, "color": GRAY}], align=PP_ALIGN.CENTER)
        if n < 6:
            arrow(slide, x + bw + Inches(0.02), y0 + bh / 2 - Inches(0.08), gap - Inches(0.04), Inches(0.16))
    textbox(slide, Inches(0.55), Inches(6.2), Inches(12.3), Inches(0.75),
            "18 model calls before judging (1 plan, 7 screening, 9 passage grading, 1 writer). Steps 1–5 never see the "
            "paper; only the step-6 judges see its answer key; the step-7 judges see only the question and the "
            "hypotheses.", size=12, color=GRAY)


def example_search_slide(prs) -> None:
    s1, s2 = T["stage1_search_plan"], T["stage2_search"]
    slide = new_slide(prs, "Real example · 2/7", "Steps 1–2: the search plan (o3-mini) and the searches", notes=(
        "The plan is stored as parsed (focused_search.parse_plan). Queries search titles and abstracts (TITLE_ABS) "
        "and add the date filter shown. The searches were replayed from the query cache and match the run exactly. "
        "Prompts: PLAN_SYSTEM and KEYWORD_SYSTEM (appendix)."))
    rows = [["Group", "Phrases written by the planner"]]
    for name, phrases in s1["output_parsed"]["groups"].items():
        rows.append([name, ", ".join(phrases)])
    table(slide, Inches(0.55), Inches(1.4), Inches(6.55), rows, [1.45, 5.1], size=11, row_height=0.37,
          bold_first_col=True)
    srows = [["Search (AND of groups)", "Hits"]]
    for s in s2["searches"]:
        srows.append([" AND ".join(s["groups"]), f"{s['hit_count']}" + (f" ({s['fetched']} used)" if
                                                                          s["fetched"] < s["hit_count"] else "")])
    fills = [None] + [PALE_RED if s["groups"] == ["material_class", "approach_3"] else None for s in s2["searches"]]
    table(slide, Inches(7.35), Inches(1.4), Inches(5.45), srows, [3.95, 1.5], size=11, row_height=0.33, fills=fills)
    textbox(slide, Inches(7.35), Inches(4.5), Inches(5.45), Inches(2.4),
            [{"text": "**The plan named the right family** (micro-alloying), but that search found 0 open-access "
                      "papers (red row).", "bullet": True, "bullet_color": RED},
             {"text": f"**Second channel:** the earlier web corpus ({s2['old_corpus_channel']['papers']} papers), "
                      "from three Llama-3.3 search phrases: " +
                      "; ".join(f"“{p}”" for p in s2["old_corpus_channel"]["output"]["phrases"]) + ".",
              "bullet": True},
             {"text": f"**{s2['admitted']} papers admitted** after the date, article-type and held-out checks "
                      f"(rejected: {s2['rejected'].get('excluded_type', 0)} wrong type, "
                      f"{s2['rejected'].get('held_out', 0)} held-out paper).", "bullet": True}], size=12, space=6)
    textbox(slide, Inches(0.55), Inches(5.7), Inches(6.55), Inches(1.25),
            [{"text": "First query, as sent to Europe PMC:", "size": 10.5, "color": GRAY, "space": 2},
             {"text": s2["searches"][0]["query"], "size": 9, "font": MONO, "color": TEXT}], space=0)


def example_screen_slide(prs) -> None:
    s3, s4 = T["stage3_screening"], T["stage4_passages"]
    graded = [(g["grade"], g["why"], p["title"]) for b in s3["batches"]
              for p, g in zip(b["input"]["papers"], b["output_parsed"]["grades"])]
    counts = {k: sum(1 for g in graded if g[0] == k) for k in (3, 2, 1, 0)}
    pg = {k: sum(1 for b in s4["batches"] for g in b["output_parsed"]["grades"] if g["grade"] == k) for k in (3, 2, 1, 0)}
    labels = s4["lever_labels_of_pack_deepseek"]
    slide = new_slide(prs, "Real example · 3/7", "Steps 3–4: screening papers and grading passages (gpt-4o)", notes=(
        "Screening: titles and abstracts (first 1,500 characters), 20 per call in a seeded random order, grades 0-3 "
        "with a reason (SCREEN_SYSTEM). Papers graded 2 or 3 are kept (at most 30), plus co-cited open-access "
        "references screened the same way (1 here, graded 1). Passages: the 6 best per paper by BM25 on the plan's "
        "phrases, graded 0-3 (PASSAGE_SYSTEM); the pack takes grade 3, then grade 2, within 64,000 characters. The "
        "replayed grading order matches the stored one exactly. Lever labels: DeepSeek with the answer key, after the "
        "run (analysis only)."))
    textbox(slide, Inches(0.55), Inches(1.38), Inches(6.4), Inches(0.75),
            f"**Screening:** 270 admitted → top 120 by word match with the plan → graded 3: **{counts[3]}**, 2: "
            f"**{counts[2]}**, 1: {counts[1]}, 0: {counts[0]} → **30 papers kept**", size=13.5, space=0)
    picks = []
    for grade in (3, 3, 2, 1, 0):
        pool = [g for g in graded if g[0] == grade and g not in picks]
        if grade == 3:
            pool = [g for g in pool if "Coating" in g[2] or "Alloying" in g[2]] or pool
        picks.append(pool[0])
    rows = [["Grade", "Paper (title)", "Screener's reason"]] + [[str(g), clip(re.sub(r"<[^>]+>", "", t), 78), clip(w, 60)]
                                                                for g, w, t in picks]
    table(slide, Inches(0.55), Inches(2.2), Inches(6.4), rows, [0.65, 3.45, 2.3], size=10.5, row_height=0.55)
    textbox(slide, Inches(7.25), Inches(1.38), Inches(5.6), Inches(0.75),
            f"**Passages:** 30 papers → 180 candidate passages (6 best per paper) → graded 3: **{pg[3]}**, 2: "
            f"**{pg[2]}**, 1: {pg[1]}, 0: {pg[0]} → **pack of {len(s4['pack'])} passages** "
            f"({s4['pack_chars']:,} characters)", size=13.5, space=0)
    by_id = {rid: (item, g["grade"]) for b in s4["batches"]
             for rid, item, g in zip(b["record_ids"], b["input"]["passages"], b["output_parsed"]["grades"])}
    cited = [rid for rid in T["stage5_writer"]["cited_ids"] if rid in by_id]
    others = [next(rid for rid, (_, grade) in by_id.items() if grade == k and rid not in cited) for k in (1, 0)]
    prow = [["Grade", "Passage (section · paper · text)"]]
    for rid in cited + others:
        item, grade = by_id[rid]
        tag = " **(cited by the writer)**" if rid in cited else ""
        prow.append([str(grade), clip(f"{item['section']} · {item['paper_title']}", 72) + tag + " — " +
                     clip(item["text"], 95)])
    table(slide, Inches(7.25), Inches(2.2), Inches(5.55), prow, [0.65, 4.9], size=10.5, row_height=0.7)
    card(slide, Inches(0.55), Inches(5.65), Inches(12.25), Inches(1.28), "Checked afterwards with the answer key",
         f"0 of the 46 packed passages mentions zirconium. DeepSeek lever labels: {labels.get('0', labels.get(0, 0))} "
         f"unrelated, {labels.get('1', labels.get(1, 0))} same kind of change with a different lever, 0 with the "
         "paper's lever. The evidence was relevant, but it could not point to the paper's choice.", PALE_RED, RED,
         body_size=13)


def example_writer_slide(prs) -> None:
    s5 = T["stage5_writer"]
    g = s5["output"]
    fx = g["falsification_experiment"]
    slide = new_slide(prs, "Real example · 4/7", "Step 5: the writer (o3-mini), input and output", notes=(
        "The writer's prompt is WRITER_B with the output schema (appendix). The input was rebuilt offline and matches "
        "the logged size exactly (72,164 characters, the same 46 evidence IDs). Citation IDs were valid (no repair). "
        "Full output: example_trace.md, section 5."))
    card(slide, Inches(0.55), Inches(1.4), Inches(4.0), Inches(5.45), "Input",
         [{"text": "**Prompt:** WRITER_B (conservative writer; appendix).", "bullet": True},
          {"text": "**JSON payload:**", "bullet": True},
          {"text": "query: the question", "bullet": True, "level": 1, "size": 12},
          {"text": "knowledge_cutoff: 2024-12-01", "bullet": True, "level": 1, "size": 12},
          {"text": "analysis_notes: { }", "bullet": True, "level": 1, "size": 12},
          {"text": "eligible_evidence: 46 passages, each with record_id, paper title, section, date and text",
           "bullet": True, "level": 1, "size": 12},
          {"text": f"**{s5['trace'][0]['chars_in']:,} characters** in; {s5['trace'][0]['seconds']:.0f} s.",
           "bullet": True},
          {"text": "Asked for one falsifiable hypothesis in a fixed JSON schema, with predictions only as far as "
                   "the evidence supports.", "bullet": True}], LIGHT, TEAL, body_size=13, space=5)
    rows = [["Field", "Output (verbatim, shortened)"],
            ["Hypothesis", clip(g["hypothesis"], 210)],
            ["Intervention", clip(g["intervention"], 170)],
            ["Structure", clip(g["structural_mediator"], 150)],
            ["Mechanism", clip(g["mechanism"], 230)],
            ["Predicted outcome", clip(g["predicted_outcome"], 170)],
            ["Falsifying test", clip(fx["design"], 120) + " Rule: " + clip(fx["falsification_rule"], 110)],
            ["Cited evidence", "2 passages of “Thermal Stability and Hot Corrosion Performance of the AlCoCrFeNi2.1 "
                               "HEA Coating by Laser Cladding” (Y/Hf co-doped coatings, 2023)"]]
    table(slide, Inches(4.8), Inches(1.4), Inches(8.0), rows, [1.55, 6.45], size=10.5, row_height=0.6,
          bold_first_col=True)
    textbox(slide, Inches(4.8), Inches(6.35), Inches(8.0), Inches(0.55),
            "The idea comes straight from the top-graded paper in the pack: a sensible, evidence-based choice.",
            size=12.5, color=TEAL)


def example_judge_input_slide(prs) -> None:
    g = T["stage5_writer"]["output"]
    key = T["stage6_reconstruction_judges"]["input"]["hidden_target"]
    slide = new_slide(prs, "Real example · 5/7", "Step 6: what the reconstruction judge sees", notes=(
        "Judge payload: {query, hidden_target (10 fields), generated_hypothesis (all fields, citation IDs relabelled "
        "E1, E2), cited_evidence (E1, E2 with paper ID, date and text)}. The same prompt (SCORE_SYSTEM) and payload "
        "go to GPT-5.6 and DeepSeek-V4-Pro. The answer key was extracted by GPT-5.6 from the paper's abstract and "
        "every section except the introduction (TARGET_SYSTEM). Full payload: example_trace.md, section 6."))
    textbox(slide, Inches(0.55), Inches(1.35), Inches(12.3), Inches(0.62),
            "Input = the question + **the paper's hidden answer key** (10 fields; 4 shown) + the hypothesis (citations "
            "relabelled E1, E2) + the cited passages. Same prompt and payload for GPT-5.6 and DeepSeek.", size=13.5,
            space=0)
    rows = [["", "The agent's hypothesis", "The paper's answer key (what the authors did and found)"],
            ["Intervention", clip(g["intervention"], 130), clip(key["intervention"], 175)],
            ["Structure", clip(g["structural_mediator"], 120), clip(key["structural_mediator"], 200)],
            ["Mechanism", clip(g["mechanism"], 150), clip(key["mechanism"], 220)],
            ["Outcome", clip(g["predicted_outcome"], 130), clip(key["actual_result"], 200)]]
    table(slide, Inches(0.55), Inches(2.1), Inches(12.25), rows, [1.45, 4.6, 6.2], size=11.5, row_height=1.08,
          bold_first_col=True, col_colors={2: NAVY})


def example_judge_output_slide(prs) -> None:
    j = T["stage6_reconstruction_judges"]
    gpt, deep = j["gpt56_output"], j["deepseek_output"]
    dims = [("problem_alignment", "Problem alignment"), ("intervention_reconstruction", "**Intervention**"),
            ("condition_agreement", "**Conditions**"), ("mechanism_agreement", "**Mechanism**"),
            ("outcome_agreement", "**Outcome**"), ("baseline_quality", "Baseline quality"),
            ("boundary_quality", "Boundary quality"), ("experiment_discriminability", "Experiment discriminability"),
            ("evidence_validity", "Evidence validity"), ("novelty", "Novelty")]
    slide = new_slide(prs, "Real example · 6/7", "Step 6: the judges' outputs", notes=(
        "GPT-5.6 returns 10 integer scores (0-4), a classification, fatal errors and an explanation; the DeepSeek "
        "cross-judge stores scores and classification. Reconstruction = mean of the four bold dimensions. Typical: "
        "GPT-5.6 mean over this arm 0.625; 0.75 is its most common value."))
    rows = [["Dimension (0–4)", "GPT-5.6", "DeepSeek"]] + [[label, str(gpt["scores"][k]), str(deep["scores"][k])]
                                                           for k, label in dims]
    rows.append(["**Reconstruction** (mean of the 4 bold)", f"**{j['reconstruction']['gpt56']:.2f}**",
                 f"**{j['reconstruction']['deepseek']:.2f}**"])
    rows.append(["Classification", gpt["classification"].replace("_", " "), deep["classification"].replace("_", " ")])
    fills = [None] + [PALE_AMBER if k in ("intervention_reconstruction", "condition_agreement", "mechanism_agreement",
                                          "outcome_agreement") else None for k, _ in dims] + [PALE_AMBER, None]
    table(slide, Inches(0.55), Inches(1.4), Inches(5.0), rows, [3.0, 1.0, 1.0], size=11.5, row_height=0.39,
          fills=fills)
    fatal = [clip(f, 150) for f in gpt["fatal_errors"]]
    textbox(slide, Inches(5.85), Inches(1.35), Inches(6.95), Inches(3.4),
            [{"text": "**GPT-5.6 fatal errors**", "size": 14, "color": RED, "space": 4}] +
            [{"text": f, "bullet": True, "size": 12, "bullet_color": RED, "space": 4} for f in fatal], size=12)
    card(slide, Inches(5.85), Inches(4.85), Inches(6.95), Inches(2.05), "GPT-5.6 explanation (excerpt)",
         "“" + clip(gpt["explanation"], 420) + "”", LIGHT, NAVY, body_size=11.5)


def example_quality_slide(prs) -> None:
    rq = T["stage7_quality_judges"]["rq"]
    pw = T["stage7_quality_judges"]["pairwise"]
    base = pw["baseline_generation"]
    slide = new_slide(prs, "Real example · 7/7", "Step 7: quality judges without the answer key", notes=(
        "RQ: RQ_SYSTEM (the expert package's scales, verbatim), input = the question and the rendered hypothesis "
        "(no citations, no evidence, no answer key); three independent DeepSeek calls, averaged. Pairwise: "
        "QUALITY_PAIR_SYSTEM, both orders; a win needs both orders to agree, otherwise the pair is a tie. The base "
        "arm (rx_base) is the same writer with the old web corpus."))
    rows = [["DeepSeek call", "Plausibility", "Testability", "Usefulness", "RQ"]]
    for n, out in enumerate(rq["outputs"], 1):
        s = out["scores"]
        rows.append([str(n), str(s["plausibility"]), str(s["testability"]), str(s["usefulness"]), f"{out['rq']:.2f}"])
    rows.append(["**Mean**", "", "", "", f"**{rq['mean_rq']:.2f}**"])
    table(slide, Inches(0.55), Inches(1.4), Inches(6.0), rows, [1.6, 1.2, 1.15, 1.15, 0.9], size=12, row_height=0.4)
    textbox(slide, Inches(0.55), Inches(3.95), Inches(6.0), Inches(1.6),
            [{"text": "Reasons (call 2):", "size": 12, "color": GRAY, "space": 3}] +
            [{"text": f"**{k.capitalize()}:** {clip(v, 150)}", "size": 11, "bullet": True, "space": 3}
             for k, v in rq["outputs"][1]["reasons"].items()], size=11)
    out = pw["outputs"]
    textbox(slide, Inches(6.85), Inches(1.35), Inches(5.95), Inches(4.3),
            [{"text": "**Pairwise vs the base arm** (same writer, old web corpus), DeepSeek:", "size": 13, "space": 4},
             {"text": f"Base hypothesis: {clip(base['intervention'], 150)}", "size": 11.5, "color": GRAY, "space": 8},
             {"text": f"**Base shown first:** picks {out['baseline_first']['winner']} (the base). "
                      f"“{clip(out['baseline_first']['reason'], 150)}”", "bullet": True, "size": 11.5, "space": 6},
             {"text": f"**Ours shown first:** picks {out['new_first']['winner']} (ours). "
                      f"“{clip(out['new_first']['reason'], 150)}”", "bullet": True, "size": 11.5, "space": 6},
             {"text": "The two orders disagree, so the pair counts as a **tie** (position bias).", "size": 12,
              "color": AMBER}], size=12)
    card(slide, Inches(0.55), Inches(5.7), Inches(12.25), Inches(1.2), "Takeaway",
         f"A sound, evidence-based proposal (research quality {rq['mean_rq']:.2f} / 4) scores "
         f"{T['stage6_reconstruction_judges']['reconstruction']['gpt56']:.2f} / 4 on reconstruction, because the "
         "paper chose zirconium, which appears nowhere in the evidence the agent could legally see.", PALE_TEAL, TEAL,
         body_size=14)


# ---------------------------------------------------------------- appendix: every prompt, verbatim

def prompt_slide(prs, title: str, columns: list[list[tuple[str, str]]], size: float = 8.5, notes: str = "") -> None:
    slide = new_slide(prs, "Appendix · prompts (verbatim)", title, section_color=GRAY, notes=notes)
    width = Inches(12.25 / len(columns) - 0.1 * (len(columns) - 1) / len(columns))
    for c, blocks in enumerate(columns):
        items = []
        for head, text in blocks:
            items.append({"text": head, "size": 11.5, "color": TEAL, "bold": True, "space": 2})
            lines = text.split("\n")
            for n, line in enumerate(lines):
                items.append({"text": line or " ", "size": size, "font": MONO, "space": 7 if n == len(lines) - 1 else 0})
        textbox(slide, Inches(0.55) + c * (width + Inches(0.1)), Inches(1.32), width, Inches(5.7), items, space=0)


def appendix(prs) -> None:
    s0 = T["stage0_benchmark_case"]
    prompt_slide(prs, "Building the benchmark case (GPT-5.6)", [
        [("Paper selection screen (title and abstract)", s0["topic_screen_system"]),
         ("Answer key from the abstract and non-introduction sections", s0["answer_key"]["system"])],
        [("Gap type of the introduction", s0["question"]["gap_system"])]], size=10,
        notes="benchmark_test2.TOPIC_SYSTEM and TARGET_SYSTEM; query_builder_v3_1.GAP_SYSTEM.")
    prompt_slide(prs, "Writing and checking the question (GPT-5.6)", [
        [("Question writer (input: the introduction without the paper's own contribution)",
          s0["question"]["writer_system"])],
        [("Leakage checker (input: the question and the answer key)", s0["question"]["checker_system"]),
         ("Lexical gate (code, not a prompt)", "Answer-word overlap after removing allowed context words must be at "
                                               "most 10%; failing levels are rewritten from the checker's phrases, "
                                               "up to 4 rounds.")]], size=9,
        notes="query_builder_v3.WRITER_SYSTEM (with LEVEL_RULES) and CHECKER_SYSTEM.")
    prompt_slide(prs, "Retrieval: planning, search phrases, screening, passage grading", [
        [("Search planner (o3-mini)", T["stage1_search_plan"]["system"]),
         ("Search phrases of the earlier web corpus (Llama-3.3)", T["stage2_search"]["old_corpus_channel"]["system"])],
        [("Paper screener (gpt-4o)", T["stage3_screening"]["system"]),
         ("Passage grader (gpt-4o)", T["stage4_passages"]["system"])]], size=9,
        notes="focused_search.PLAN_SYSTEM, SCREEN_SYSTEM, PASSAGE_SYSTEM; citegraph.KEYWORD_SYSTEM.")
    prompt_slide(prs, "The writer and the judges", [
        [("Writer: WRITER_B with the output schema (o3-mini)", T["stage5_writer"]["system"])],
        [("Reconstruction judge, sees the answer key (GPT-5.6, DeepSeek-V4-Pro)",
          T["stage6_reconstruction_judges"]["system"])],
        [("Pairwise quality judge, no answer key (DeepSeek, o1, GPT-5.6)",
          T["stage7_quality_judges"]["pairwise"]["system"])]],
        size=8.5, notes="loop_methods.WRITER_B; temporal_hypothesis_benchmark._SCORE_SYSTEM; "
                        "diag_analysis.QUALITY_PAIR_SYSTEM.")
    rq_text = T["stage7_quality_judges"]["rq"]["system"]
    cut = rq_text.index("Rate the hypothesis on three")
    prompt_slide(prs, "Research-quality judge (DeepSeek, three calls)", [
        [("RQ judge (1/2)", rq_text[:cut].rstrip())], [("RQ judge (2/2)", rq_text[cut:])]], size=9,
        notes="rq_judge.RQ_SYSTEM: the expert package's instructions and scales, verbatim (loop.md 24.1). Input: the "
              "question and the hypothesis as the expert sees it.")


def main() -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    title_slide(prs)
    task_slide(prs)
    run_slide(prs)
    excels_slide(prs)
    fails_slide(prs)
    why_slide(prs)
    next_slide(prs)
    example_input_slide(prs)
    example_search_slide(prs)
    example_screen_slide(prs)
    example_writer_slide(prs)
    example_judge_input_slide(prs)
    example_judge_output_slide(prs)
    example_quality_slide(prs)
    appendix(prs)
    prs.save(OUT)
    print(f"wrote {OUT} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
