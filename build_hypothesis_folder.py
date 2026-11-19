"""Export the per-paper method's outputs (loop.md 28.3) as hypotheses/1 ... hypotheses/45, numbered as in test/.

Each folder holds, for the paper's three research questions (levels broad, problem_constrained, expert_context):
  paper.pdf                 the target paper (the same file as test/N/paper.pdf; never shown to any agent)
  question.json             the questions and knowledge cutoff (the same file as test/N/question.json)
  internal_reasoning.json   every step of the agents: retrieved papers, each paper's background, every round's
                            hypotheses and critique, the merged pool and every tournament match
  hypotheses.json           every accepted hypothesis (after merging near-duplicates), in tournament order
  final_hypothesis.json     the method's answer: the rank-1 hypothesis, plus the ranked top 3

Runs come from loop_rx/perpaper_full (sample 1). A level whose run has not finished is marked "pending".

    ./.venv/bin/python build_hypothesis_folder.py
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
TEST = ROOT / "test"
OUT = ROOT / "hypotheses"
RUNS = ROOT / "experiments" / "high_temperature_hea_qwen35b" / "loop_rx" / "perpaper_full" / "runs"
ARM, SAMPLE = "perpaper_full", 1
LEVELS = ("broad", "problem_constrained", "expert_context")
METHOD = ("Per-paper generate -> critique -> narrow (loop.md 28.1, 28.3). For the research question, the 10 most "
          "relevant papers published before the knowledge cutoff are retrieved. For each paper, o3-mini writes 3 "
          "hypotheses that build on it, using teaching-text passages and MatKG facts as background; a critic "
          "(o3-mini, high reasoning effort) that sees the paper and background but never the question checks each "
          "for soundness, testability and going beyond the paper; the generator revises until at least one is "
          "accepted (at most 20 rounds, else the paper is dropped). The accepted hypotheses of all papers, "
          "near-duplicates merged, meet in a pairwise tournament on the question (o3-mini, high effort; both orders, "
          "a win needs both). Rank 1 is the final hypothesis.")


def write(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def place(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def load_run(paper_id: str, level: str) -> dict[str, Any] | None:
    path = RUNS / f"{paper_id}__{level}__{ARM}__s{SAMPLE}.json"
    if not path.exists():
        return None
    run = json.loads(path.read_text())
    return run if run.get("status") == "ok" else {"status": run.get("status"), "error": run.get("error")}


def source_of(run: dict[str, Any], pmcid: str) -> dict[str, Any]:
    for paper in run["notes"].get("selected_papers", []):
        if paper["pmcid"] == pmcid:
            return {k: paper.get(k) for k in ("pmcid", "title", "doi", "date")}
    return {"pmcid": pmcid}


def candidate(run: dict[str, Any], item: dict[str, Any], rank: int | None) -> dict[str, Any]:
    return {"label": item.get("label"), "tournament_rank": rank, "source_paper": source_of(run, item["paper"]),
            "accepted_in_round": item["round"], "builds_on": item["builds_on"], "what_is_new": item["what_is_new"],
            "hypothesis": {k: v for k, v in item["fields"].items() if k != "citation_validation"}}


def ranked_pool(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Tournament order: the final round robin's order for its candidates, then the others by Swiss points (pool
    order breaks ties)."""
    notes = run["notes"]
    pool = notes.get("pool", [])
    swiss = notes.get("tournament", {}).get("swiss_points") or [0.0] * len(pool)
    final = notes.get("ranking", [])
    rest = sorted((n for n, c in enumerate(pool) if c["label"] not in final), key=lambda n: (-swiss[n], n))
    labels = final + [pool[n]["label"] for n in rest]
    by_label = {c["label"]: c for c in pool}
    return [candidate(run, by_label[label], rank) for rank, label in enumerate(labels, 1)]


def reasoning(run: dict[str, Any]) -> dict[str, Any]:
    notes = run["notes"]
    return {
        "retrieved_papers": notes.get("selected_papers", []),
        "per_paper": [{
            "paper": p["paper"], "title": p.get("title"), "relevance_grade": p.get("grade"),
            "paper_text_chars": p.get("paper_chars"), "background": p.get("background_items", []),
            "outcome": ("dropped after %d rounds" % p.get("n_rounds", 0)) if not p.get("n_accepted") else
                       f"{p['n_accepted']} accepted in round {p.get('n_rounds')}",
            **({"error": p["error"]} if p.get("error") else {}),
            "rounds": [{"round": r["round"], "hypotheses": r.get("hypotheses", []),
                        "critic_notes_on_the_paper": r.get("critic_summary", {}),
                        "critique": r.get("reviews", [])} for r in p.get("rounds", [])],
        } for p in notes.get("papers", [])],
        "summary": notes.get("summary"),
        "narrowing": {"candidates_after_merging": len(notes.get("pool", [])),
                      "accepted_before_merging": notes.get("accepted_before_dedupe"),
                      "format": notes.get("tournament", {}).get("format"),
                      "points": {k: v for k, v in notes.get("tournament", {}).items() if k != "format"},
                      "ranking": notes.get("ranking", []), "matches": notes.get("matches", [])},
        "cost": {"llm_calls": run.get("llm_calls"), "minutes": round(run.get("elapsed_seconds", 0) / 60, 1),
                 "models": run.get("models")},
        "leakage_audit": run.get("audit"),
    }


def build() -> dict[str, Any]:
    index = json.loads((TEST / "index.json").read_text())
    status = {"ok": 0, "pending": 0, "failed": 0}
    rows = []
    for entry in index:
        n, pid = entry["number"], entry["paper_id"]
        folder = OUT / str(n)
        folder.mkdir(parents=True, exist_ok=True)
        place(TEST / str(n) / "paper.pdf", folder / "paper.pdf")
        place(TEST / str(n) / "question.json", folder / "question.json")
        question = json.loads((TEST / str(n) / "question.json").read_text())
        head = {"number": n, "paper_id": pid, "knowledge_cutoff": question["knowledge_cutoff"], "method": ARM}
        internal, hyps, final = dict(head, method_description=METHOD), dict(head), dict(head)
        for level in LEVELS:
            run = load_run(pid, level)
            q = question["questions"][level]
            if run is None or "notes" not in run:
                state = "pending" if run is None else "failed"
                status[state] += 1
                for d in (internal, hyps, final):
                    d[level] = {"question": q, "status": state, **({"error": run["error"]} if run else {})}
                continue
            status["ok"] += 1
            pool = ranked_pool(run)
            internal[level] = {"question": q, "status": "ok", **reasoning(run)}
            hyps[level] = {"question": q, "status": "ok", "count": len(pool), "hypotheses": pool}
            final[level] = {"question": q, "status": "ok", "final_hypothesis": pool[0] if pool else None,
                            "top3": pool[:3],
                            "rank1_tied": run["notes"].get("tournament", {}).get("rank1_tied"),
                            "cited_evidence": run.get("cited_evidence", [])}
        write(folder / "internal_reasoning.json", internal)
        write(folder / "hypotheses.json", hyps)
        write(folder / "final_hypothesis.json", final)
        rows.append((n, entry["split"], pid, entry["title"],
                     [final[lv].get("status") for lv in LEVELS],
                     (final["problem_constrained"].get("final_hypothesis") or {}).get("hypothesis", {}).get(
                         "hypothesis", "")))
    readme(rows, status)
    return status


def readme(rows: list[tuple], status: dict[str, int]) -> None:
    lines = [
        "# Hypotheses for the 45 test papers", "",
        "Outputs of the per-paper generate → critique → narrow method (loop.md sections 28.1–28.3) for every paper in "
        "[`test/`](../test/), with the same numbering. One run (sample 1) per research question; each paper has three "
        "questions (levels `broad`, `problem_constrained`, `expert_context`). No agent ever saw the target paper: "
        "all evidence was published before the knowledge cutoff, and every run's leakage audit is stored.", "",
        "## Files in each folder", "",
        "| File | Content |", "|---|---|",
        "| `paper.pdf` | The target paper (for reading; never shown to any agent). |",
        "| `question.json` | The three research questions and the knowledge cutoff (keys explained in "
        "[test/README.md](../test/README.md)). |",
        "| `internal_reasoning.json` | Every step, per question level: the 10 retrieved papers; for each paper its "
        "background passages (teaching texts and MatKG facts), every round's hypotheses and the critic's notes on "
        "the paper (what it did, reported, proposed) and critique (pass/fail with reasons for `sound`, `testable` and "
        "`beyond_paper`, a quote and a fix); the outcome (accepted in round k, or dropped); the tournament's matches "
        "with both orders' reasons; cost and leakage audit. These are the agents' written outputs; o3-mini's hidden "
        "reasoning tokens are not available. |",
        "| `hypotheses.json` | Every accepted hypothesis (near-duplicates merged), in tournament order (ranks 1–5 from "
        "the final round robin, the rest by Swiss-round points), each with its source paper, the round it was accepted in, what it builds on and what is new. |",
        "| `final_hypothesis.json` | The method's answer per level: `final_hypothesis` (rank 1), the ranked `top3`, "
        "whether rank 1 was tied, and the text of the passages it cites. |", "",
        "Each hypothesis has the shared fields: `hypothesis`, `material_initial_state`, `intervention`, `conditions`, "
        "`structural_mediator`, `mechanism`, `predicted_outcome`, `baseline`, `boundary`, `uncertainty`, "
        "`supporting_evidence_ids`, `conflicting_evidence_ids` and `falsification_experiment` (`design`, "
        "`measurements`, `falsification_rule`). Evidence IDs: `PMC…::web::…` = a passage of a retrieved paper, "
        "`TXT::…` = a teaching-text passage, `KG::…` = a MatKG fact.", "",
        f"Status: {status['ok']} of {status['ok'] + status['pending'] + status['failed']} question runs complete"
        + (f", {status['pending']} pending" if status["pending"] else "")
        + (f", {status['failed']} failed" if status["failed"] else "") + ". These runs are not scored; the "
        "method's pilot evaluation is in loop.md 28.2. Built by `build_hypothesis_folder.py`.", "",
        "| # | Split | Paper | Title | Levels done | Final hypothesis (problem-constrained question) |",
        "|---:|---|---|---|---|---|"]
    for n, split, pid, title, states, hyp in rows:
        done = sum(s == "ok" for s in states)
        lines.append(f"| [{n}]({n}/) | {split} | {pid} | {title.replace('|', '/')[:90]} | {done}/3 | "
                     f"{hyp.replace('|', '/')[:220]} |")
    (OUT / "README.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    print(build())
