"""A fresh, fully logged run of the draft-then-ground agent (agent_draft_ground_b_o3mini) for the 2026-11-10 deck, on
the same question as the deck's earlier example (PMC11643467, problem-constrained). The 270 stored runs of this agent
did not keep the closed-book draft, so the deck's step-by-step example is this demonstration run, labelled as such; all
reported scores are those of the stored runs.

    ./.venv/bin/python presentations/2026-11-10_on_demand_retrieval/draft_example.py     # 2 o3-mini calls
writes draft_example.json next to this file.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.setdefault("MATHG_LOOP_ROOT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_root"))

import quality_eval as Q  # noqa: E402,I001

import json  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import citegraph as cg  # noqa: E402
import hypo_loop as H  # noqa: E402
import loop_methods as LM  # noqa: E402
import websearch as ws  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "draft_example.json"
PID, LEVEL, SAMPLE = "PMC11643467", "problem_constrained", 1
METHOD = "agent_draft_ground_b_o3mini"


class LoggedHarness(H.Harness):
    """Records every model call: role, system prompt, input payload and raw output."""

    def __init__(self, *a: Any, **k: Any) -> None:
        super().__init__(*a, **k)
        self.log: list[dict[str, Any]] = []

    def ask(self, role: str, model: str, system: str, payload: dict[str, Any], max_out: int | None = None) -> Any:
        raw = super().ask(role, model, system, payload, max_out)
        self.log.append({"role": role, "model": H.MODELS[model]["deployment"], "system": system, "input": payload,
                         "output": raw})
        return raw


def run() -> None:
    case = H.cases()[PID]
    h = LoggedHarness(case, LEVEL, SAMPLE)
    generation = LM.m_agent(h, choose=False, ground=True)
    corpus = json.loads(Path(f"{ws.corpus_stem(PID, LEVEL)}.json").read_text())
    phrases = json.loads(Path(f"{ws.corpus_stem(PID, LEVEL)}.phrases.json").read_text())
    pool = h.pool("text_chunks")
    draft = next(c["output"] for c in h.log if c["role"] == "draft")
    search = " ".join(str(draft.get(f) or "") for f in ("intervention", "structural_mediator", "mechanism"))
    run_record = {"run_id": f"{PID}__{LEVEL}__{METHOD}__demo", "paper_id": PID, "query_level": LEVEL, "sample": SAMPLE,
                  "method": METHOD, "query": h.query, "generation": generation, "seen_ids": sorted(h.seen),
                  "cited_ids": sorted(set(generation.get("supporting_evidence_ids", []) +
                                          generation.get("conflicting_evidence_ids", []))),
                  "audit": H.leakage_audit(h, []), "models": h.models, "notes": h.notes, "trace": h.trace}
    run_record["cited_evidence"] = [{"record_id": c, "paper_id": h.seen[c].paper_id,
                                     "publication_date": h.seen[c].publication_date, "kind": h.seen[c].kind,
                                     "text": h.seen[c].text[:1200]} for c in run_record["cited_ids"] if c in h.seen]
    out = {"note": "demonstration run made on 2026-11-10 for the deck; the agent's scores come from its 270 stored runs",
           "question": h.query, "cutoff": h.cutoff, "calls": h.log, "run": run_record,
           "search": {"keyword_system": cg.KEYWORD_SYSTEM, "phrases": phrases["phrases"],
                      "phrase_writer": phrases.get("writer"), "searches": corpus["searches"],
                      "unique_hits": corpus["unique_hits"], "seeds": len(corpus["seeds"]),
                      "expansion": len(corpus.get("expansion", [])), "rejected": corpus.get("rejected", {}),
                      "date_filter": ws.filters(case["publication_date"])},
           "pool": {"passages": len(pool), "papers": len({r.paper_id for r in pool})},
           "ranking": {"search_text": search, "pack": h.notes.get("focused_pack"),
                       "packed": [{"record_id": r.record_id, "title": str((r.structured or {}).get("title", ""))[:150],
                                   "section": r.kind.split(":", 1)[-1]} for r in h.seen.values()]}}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT}; calls {[c['role'] for c in h.log]}; pack {h.notes.get('focused_pack')}; audit {run_record['audit']}")


if __name__ == "__main__":
    run()
