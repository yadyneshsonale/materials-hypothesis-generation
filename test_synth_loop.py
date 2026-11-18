"""Tests for experiment 48 (loop.md 27.7): the synthesis writers (synth_loop.py). No API calls."""

from __future__ import annotations

import random
import unittest
from typing import Any
from unittest.mock import patch

import synth_loop as SL
from temporal_hypothesis_benchmark import RetrievalRecord

RECORDS = [RetrievalRecord(f"P{n}::web::{n:03d}::results", f"P{n}", "2020-01-01", "web:Results", f"passage {n}",
                           {"source": "web", "title": f"Paper {n}"}) for n in (1, 2)]


class FakeHarness:
    def __init__(self, map_answer: Any = None) -> None:
        self.query, self.cutoff, self.level, self.sample = "q", "2024-06-01", "broad", 1
        self.case = {"paper_id": "PMCX"}
        self.rng = random.Random(1)
        self.seen: dict[str, RetrievalRecord] = {}
        self.notes: dict[str, Any] = {}
        self.models: dict[str, str] = {}
        self.trace: list[dict[str, Any]] = []
        self.source = "web"
        self.map_answer = map_answer
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def ask(self, role: str, model: str, system: str, payload: dict[str, Any], max_out: int | None = None) -> Any:
        self.calls.append((role, system, payload))
        return self.map_answer

    def generate_final(self, role: str, model: str, system: str, payload: dict[str, Any], allowed: set[str],
                       citation_repair: str = "regenerate") -> dict[str, Any]:
        self.calls.append((role, system, payload))
        self.allowed = allowed
        return {"hypothesis": "h"}


def fake_pack(h: Any, focused: bool, budget: int) -> list[RetrievalRecord]:
    assert focused
    for r in RECORDS:
        h.seen[r.record_id] = r
    return list(RECORDS)


class SynthTests(unittest.TestCase):
    def test_synth_a_is_one_call_with_the_focused_pack(self) -> None:
        h = FakeHarness()
        with patch.object(SL.RL, "start_pack", fake_pack):
            SL.m_synth(h, mapped=False)
        self.assertEqual([c[0] for c in h.calls], ["writer"])
        role, system, payload = h.calls[0]
        self.assertIs(system, SL.SYNTH_A)
        self.assertEqual(list(payload), ["query", "knowledge_cutoff", "eligible_evidence"])
        self.assertEqual(h.allowed, {r.record_id for r in RECORDS})

    def test_synth_b_maps_then_writes_with_the_map(self) -> None:
        answer = {"done": [{"study": "x"}], "proposed": [], "gaps": ["g"], "conflicts": "not a list"}
        h = FakeHarness(answer)
        with patch.object(SL.RL, "start_pack", fake_pack):
            SL.m_synth(h, mapped=True)
        self.assertEqual([c[0] for c in h.calls], ["map", "writer"])
        self.assertIs(h.calls[1][1], SL.SYNTH_B)
        self.assertEqual(h.calls[1][2]["literature_map"]["conflicts"], [])
        self.assertEqual(h.notes["literature_map"], {"done": 1, "proposed": 0, "gaps": 1, "conflicts": 0})
        h2 = FakeHarness("garbage")
        with patch.object(SL.RL, "start_pack", fake_pack):
            SL.m_synth(h2, mapped=True)
        self.assertEqual(h2.calls[1][2]["literature_map"], {"done": [], "proposed": [], "gaps": [], "conflicts": []})

    def test_prompts_forbid_copying_and_are_not_judge_prompts(self) -> None:
        import diag_analysis as D
        import noncopy_eval as N
        for system in (SL.SYNTH_A, SL.SYNTH_B):
            self.assertIn("at least two different papers", system)
            self.assertIn("future work", system)
            self.assertNotIn(N.NONCOPY_SYSTEM[:80], system)
            self.assertNotIn(D.QUALITY_PAIR_SYSTEM[:80], system)


if __name__ == "__main__":
    unittest.main()
