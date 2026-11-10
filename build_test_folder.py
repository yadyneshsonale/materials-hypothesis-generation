"""Lay out the 45 benchmark papers as test/1 ... test/45, each with paper.pdf, paper.xml and question.json.

Numbering follows the splits in the order they were built: dev 1-8, test 9-12, test2 13-24, test3 25-36, test4 37-45
(paper IDs ascending within a split). question.json holds the three research questions written from the paper's
introduction (its own contribution removed) and the knowledge cutoff; the answer key (hidden_target) is left out.
PDFs come from the existing pipeline copies or, if missing, from the PMC open-access bucket (MD5-checked).

    ./.venv/bin/python build_test_folder.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import arrange_paper_outputs as A

ROOT = Path(__file__).resolve().parent
E = ROOT / "experiments" / "high_temperature_hea_qwen35b"
OUT = ROOT / "test"
SETS = [("benchmark_v3_1", ("validation",), "dev"), ("benchmark_v3_1", ("test",), "test"),
        ("benchmark_test2", ("test2",), "test2"), ("benchmark_test3", ("test3",), "test3"),
        ("benchmark_test4", ("test4",), "test4")]
LEVELS = ("broad", "problem_constrained", "expert_context")
# Open-access papers whose PDF is not in the PMC open-access bucket: the publisher's PDF.
PUBLISHER_PDF = {"PMC10920630": "https://www.nature.com/articles/s41598-024-55962-1.pdf"}


def first(*paths: Path) -> Path | None:
    return next((p for p in paths if p.exists()), None)


def text_of(xml: str, tag: str) -> str:
    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", xml, re.S)
    return " ".join(re.sub(r"<[^>]+>", "", m.group(1)).split()) if m else ""


def place(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    try:
        os.link(src, dst)  # same blob in git; a hard link saves local disk
    except OSError:
        shutil.copy2(src, dst)


def entries() -> list[dict]:
    rows = []
    for bench, splits, name in SETS:
        cases = [json.loads(p.read_text()) for p in sorted((E / bench / "cases").glob("PMC*.json"))]
        for case in sorted((c for c in cases if c["split"] in splits), key=lambda c: c["paper_id"]):
            rows.append({"case": case, "bench": bench, "split": name})
    for n, row in enumerate(rows, 1):
        row["number"] = n
    return rows


def build(row: dict) -> dict:
    case, pid = row["case"], row["case"]["paper_id"]
    folder = OUT / str(row["number"])
    folder.mkdir(parents=True, exist_ok=True)
    xml = first(E / row["bench"] / "papers" / pid / "input" / "article.xml",
                E / "outputs" / "papers" / pid / "input" / "article.xml")
    if xml is None:
        raise FileNotFoundError(f"no XML for {pid}")
    place(xml, folder / "paper.xml")
    pdf = first(E / "outputs" / "papers" / pid / "input" / "article.pdf",
                E / row["bench"] / "papers" / pid / "input" / "article.pdf")
    if pdf is not None:
        place(pdf, folder / "paper.pdf")
        pdf_source = "pipeline copy (PMC open-access bucket)"
    elif pid in PUBLISHER_PDF:
        pdf_source = PUBLISHER_PDF[pid]
        if not (folder / "paper.pdf").exists():
            request = urllib.request.Request(pdf_source, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=300) as response:
                data = response.read()
            if not data.startswith(b"%PDF-"):
                raise ValueError(f"{pid}: publisher download is not a PDF")
            (folder / "paper.pdf").write_bytes(data)
    else:
        meta = A._resolve_metadata(pid)
        if not (folder / "paper.pdf").exists():
            A._download_pdf(meta, folder / "paper.pdf")
        pdf_source = meta["pdf_url"].split("?")[0]
    raw = xml.read_text(errors="replace")
    title, doi = text_of(raw, "article-title"), (re.search(r'<article-id pub-id-type="doi">([^<]+)<', raw) or [None, ""])[1]
    question = {
        "number": row["number"], "paper_id": pid, "title": title, "doi": doi, "retracted": title.upper().startswith("RETRACTED"),
        "publication_date": case["publication_date"], "knowledge_cutoff": case["publication_date"],
        "split": row["split"],
        "questions": {lvl: case["queries"][lvl]["text"] for lvl in LEVELS},
        "levels": {"broad": "the problem area only", "problem_constrained": "adds the material and its limitation",
                   "expert_context": "adds the background an expert would know"},
        "gap": case.get("gap"),
        "how_written": {"source": case.get("query_source"), "writer": case.get("query_writer"),
                        "leakage_checker": case.get("leakage_checker"),
                        "rewrite_rounds": case.get("rounds"),
                        "passed_leakage_check": {lvl: bool(case["queries"][lvl].get("passed_gate")) for lvl in LEVELS},
                        "answer_word_overlap": {lvl: case["queries"][lvl].get("overlap") for lvl in LEVELS}},
    }
    (folder / "question.json").write_text(json.dumps(question, indent=2, ensure_ascii=False) + "\n")
    return {"number": row["number"], "paper_id": pid, "split": row["split"], "publication_date":
            case["publication_date"], "title": title, "doi": doi, "pdf_source": pdf_source}


def main() -> None:
    rows = entries()
    assert len(rows) == 45, len(rows)
    with ThreadPoolExecutor(4) as pool:
        index = list(pool.map(build, rows))
    (OUT / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    lines = ["# Test set: 45 papers", "",
             "The papers whose questions all methods were evaluated on (loop.md section 27). Each folder `N/` holds:", "",
             "- `paper.pdf`: the published article (for reading; the pipeline never uses it).",
             "- `paper.xml`: the open-access JATS XML.",
             "- `question.json`: the three research questions written from the paper's introduction with its own "
             "contribution removed (levels `broad`, `problem_constrained`, `expert_context`), the knowledge cutoff "
             "(the paper's publication date: methods may only use evidence published before it), the gap the "
             "introduction states, and how the questions were written and leak-checked. The answer key is not included.",
             "", "## Keys of question.json", "",
             "| Key | Meaning |", "|---|---|",
             "| `number` | The folder number (1–45). |",
             "| `paper_id` | The paper's PubMed Central ID. |",
             "| `title`, `doi` | The paper's title and DOI, from its XML. |",
             "| `retracted` | `true` if the paper has since been retracted. |",
             "| `publication_date` | The paper's publication date, as used by the benchmark. |",
             "| `knowledge_cutoff` | The date the methods must respect (here, the publication date): they may only use "
             "evidence published strictly before it, so they cannot have seen the paper. |",
             "| `split` | The batch the paper belongs to. `dev` was used to develop methods; `test`, `test2`, `test3` and "
             "`test4` were held out and each used once for pre-registered final runs. All are now used up, so results on "
             "them are development results. |",
             "| `questions` | The three research questions given to the methods, one at a time, with the knowledge cutoff. "
             "Each is written from the paper's introduction only, never from its results. |",
             "| `questions.broad` | Names only the problem area and goal (e.g. an alloy family and application). |",
             "| `questions.problem_constrained` | Adds the specific starting material, its limitation and the constraints. |",
             "| `questions.expert_context` | Adds the background an expert would know: earlier results and why they fall "
             "short. |",
             "| `levels` | Short descriptions of the three question levels. |",
             "| `gap` | The limitation or open question the introduction states, which the questions ask to address. |",
             "| `gap.gap_type` | `design` (a property to improve; 22 papers), `understanding` (a behaviour or mechanism to "
             "explain; 20) or `method` (a better method, model or measurement; 3). |",
             "| `gap.evidence` | The sentence from the introduction that states the gap. |",
             "| `gap.reason` | Why that sentence was read as this kind of gap. |",
             "| `gap.classifier` | The model that classified the gap. |",
             "| `how_written` | How the questions were made and checked for leakage. |",
             "| `how_written.source` | `introduction_without_own_contribution`: the introduction, cut at the first sentence "
             "about the paper's own work (\"in this work…\"), so the questions never describe the paper's answer. |",
             "| `how_written.writer` | The model that wrote the questions (`trapi:` = accessed through Microsoft's TRAPI "
             "service). |",
             "| `how_written.leakage_checker` | The model that saw both the question and the paper's answer and flagged any "
             "phrase that gives the answer away (or steers towards it). |",
             "| `how_written.rewrite_rounds` | How many write-and-check rounds the paper's questions took: a flagged question "
             "was rewritten without the flagged phrases, up to 4 rounds. For papers whose gap is not `design`, the questions "
             "were then rewritten with a prompt for that gap type, up to 4 more rounds (so up to 8 in total). |",
             "| `how_written.passed_leakage_check` | Per question: `true` if it passed both the checker and the word-overlap "
             "limit. 127 of the 135 questions passed; 8 still had a checker flag after the last round and were kept "
             "and marked `false` (papers 7, 16, 17, 25, 40, 41, 43; all within the overlap limit). |",
             "| `how_written.answer_word_overlap` | Per question: the share of the answer's content words (intervention, "
             "mechanism, outcome…) that appear in the question, ignoring words that describe the allowed context such as "
             "the starting material. Must be ≤ 0.10. |",
             "", "Note: paper 25 (PMC10920630, Scientific Reports 2024) has since been retracted; it is kept so that the "
             "set matches every reported result (`retracted: true` in its question.json).",
             "", "Built by `build_test_folder.py`; source cases in `experiments/high_temperature_hea_qwen35b/benchmark_*`.",
             "", "| # | Split | Paper | Published | Title |", "|---:|---|---|---|---|"]
    lines += [f"| [{r['number']}]({r['number']}/) | {r['split']} | {r['paper_id']} | {r['publication_date']} | "
              f"{r['title'].replace('|', '/')} |" for r in index]
    (OUT / "README.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {len(index)} folders to {OUT}")


if __name__ == "__main__":
    main()
