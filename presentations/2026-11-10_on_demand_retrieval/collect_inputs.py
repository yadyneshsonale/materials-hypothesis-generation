"""Collect everything the 2026-11-10 deck shows that is not already in the 2026-11-04 example trace: the evaluation
prompts, the cost of the agent's retrieval per question (from the 135 focused-corpus manifests), and the final
experiment-46 results (loop_quality/analysis_quality.json). Offline: reads stored files only.

    ./.venv/bin/python presentations/2026-11-10_on_demand_retrieval/collect_inputs.py
writes deck_inputs.json next to this file.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import quality_eval as Q  # noqa: E402,I001 - first: it sets the case and loop roots

import json  # noqa: E402
import statistics  # noqa: E402
from collections import Counter  # noqa: E402
from pathlib import Path  # noqa: E402

import diag_analysis as D  # noqa: E402
import rq_judge as RQ  # noqa: E402

E = Path("experiments/high_temperature_hea_qwen35b")
HERE = Path(__file__).resolve().parent


def mean(values: list[float]) -> float:
    return round(statistics.fmean(values), 1)


def retrieval_cost() -> dict:
    manifests = [json.loads(p.read_text()) for p in sorted((E / "websearch" / "focused").glob("PMC*/*.json"))]
    runs = [json.loads(p.read_text()) for p in sorted((E / "loop_rx" / "rx_r" / "runs").glob("PMC*.json"))]
    roles = Counter(t["role"] for m in manifests for t in m["trace"])
    return {
        "questions": len(manifests),
        "calls_per_question": {role: round(n / len(manifests), 1) for role, n in roles.items()},
        "retrieval_calls_per_question": mean([len(m["trace"]) for m in manifests]),
        "retrieval_chars_in_per_question": mean([sum(t.get("chars_in", 0) for t in m["trace"]) for m in manifests]),
        "searches_per_question": mean([len(m["searches"]) for m in manifests]),
        "search_hits_per_question": mean([m["unique_hits"] for m in manifests]),
        "earlier_corpus_papers_per_question": mean([m["old_corpus_papers"] for m in manifests]),
        "admitted_per_question": mean([m["admitted"] for m in manifests]),
        "screened_per_question": mean([m["screened"] for m in manifests]),
        "papers_kept_per_question": mean([len(m["papers"]) for m in manifests]),
        "passages_graded_per_question": mean([len(m["passage_grades"]) for m in manifests]),
        "pack_passages_per_question": mean([len(m["pack"]) for m in manifests]),
        "pack_chars_per_question": mean([m["pack_chars"] for m in manifests]),
        "screen_grades": dict(Counter(v["grade"] for m in manifests for v in m["screen_grades"].values())),
        "passage_grades": dict(Counter(v for m in manifests for v in m["passage_grades"].values())),
        "distinct_papers_used": len({p["pmcid"] for m in manifests for p in m["papers"]}),
        "writer_chars_in_per_run": mean([r["chars_in"] for r in runs]),
        "writer_seconds_per_run": mean([r["elapsed_seconds"] for r in runs]),
    }


def draft_cost() -> dict:
    """The draft-then-ground agent (agent_draft_ground_b_o3mini): its per-question web corpus (experiment 36, built by
    search) and its 270 stored runs."""
    import hypo_loop as H
    import websearch as ws
    hits, admitted, seeds, expansion, papers, passages = [], [], [], [], [], []
    for case, level in H.units("all36") + H.units("test4"):
        manifest = json.loads(Path(f"{ws.corpus_stem(case['paper_id'], level)}.json").read_text())
        hits.append(manifest["unique_hits"])
        admitted.append(manifest["candidates_after_filters"])
        seeds.append(len(manifest["seeds"]))
        expansion.append(len(manifest.get("expansion", [])))
        records = ws.case_records(case["paper_id"], level, "text_chunks")
        passages.append(len(records))
        papers.append(len({r.paper_id for r in records}))
    runs = RQ.runs_of("agent_draft_ground_b_o3mini")
    packs = [r["notes"]["focused_pack"] for r in runs]
    return {"questions": len(hits), "search_hits": mean(hits), "admitted": mean(admitted), "seeds": mean(seeds),
            "expansion": mean(expansion), "corpus_papers": mean(papers), "corpus_passages": mean(passages),
            "pack_passages": mean([x["records"] for x in packs]), "pack_papers": mean([x["papers"] for x in packs]),
            "pack_chars": mean([x["chars"] for x in packs]), "calls_per_run": mean([r["llm_calls"] for r in runs]),
            "chars_in": mean([r["chars_in"] for r in runs]), "seconds": mean([r["elapsed_seconds"] for r in runs]),
            "cited": mean([len(r["cited_ids"]) for r in runs])}


def main() -> None:
    analysis = json.loads((E / "loop_quality" / "analysis_quality.json").read_text())
    rows = analysis["rows"]
    out = {
        "prompts": {"RQ_SYSTEM": RQ.RQ_SYSTEM, "GROUNDING_SYSTEM": Q.GROUNDING_SYSTEM,
                    "QUALITY_PAIR_SYSTEM": D.QUALITY_PAIR_SYSTEM},
        "cost": retrieval_cost(),
        "cost_draft": draft_cost(),
        "results": {
            "incumbent": analysis["incumbent"],
            "grounding_validation": {k: analysis["grounding_validation"][k] for k in
                                     ("checks", "valid", "G3_retest")},
            "g1": analysis["grounding_validation"]["G1_swap"],
            "g2": analysis["grounding_validation"]["G2_removal"],
            "g4": analysis["grounding_validation"]["G4_known_groups"],
            "controls": analysis["rq_controls_this_session"]["three_calls"],
            "rows": {m: {k: r[k] for k in ("sp", "rq", "scales", "grounding", "words", "pairwise", "experiment")}
                     | {"sp_vs_writer": r.get("sp_vs_writer", {})} for m, r in rows.items()},
            "references": {m: {k: r[k] for k in ("sp", "rq", "grounding", "pairwise")}
                           for m, r in analysis["references"].items()},
            "configurations": len(rows),
        },
    }
    (HERE / "deck_inputs.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out["cost"], indent=1))


if __name__ == "__main__":
    main()
