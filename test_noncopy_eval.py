"""Tests for experiment 47 (loop.md 27.5): the non-copying judge (noncopy_eval.py). No API calls."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import noncopy_eval as N
from temporal_hypothesis_benchmark import RetrievalRecord


def rec(n: int) -> RetrievalRecord:
    return RetrievalRecord(f"P{n}X::web::{n:03d}::results", f"P{n}X", "2020-01-01", "web:Results", f"passage {n}",
                           {"source": "web", "title": f"Paper {n}"})


RECORDS = [rec(1), rec(2), rec(3)]
RUN = {"run_id": "PMCX__broad__rx_r__s1", "paper_id": "PMCX", "query_level": "broad", "method": "rx_r", "query": "q",
       "seen_ids": sorted(r.record_id for r in RECORDS),
       "generation": {"hypothesis": "h", "supporting_evidence_ids": [RECORDS[2].record_id], "conflicting_evidence_ids": [],
                      "citation_validation": {"status": "valid"}}}
VALID = {"provenance": {"intervention": "P3", "overall_idea": "P3"}, "copied_elements": ["x"],
         "non_copying_reason": "r", "non_copying": 2}


class NonCopyTests(unittest.TestCase):
    def test_view_relabels_and_blinds(self) -> None:
        with patch.object(N, "pack", return_value=RECORDS):
            v = N.view(RUN)
        self.assertEqual(v["generation"]["supporting_evidence_ids"], ["P3"])
        self.assertNotIn("citation_validation", v["generation"])
        self.assertEqual([p["id"] for p in v["passages"]], ["P1", "P2", "P3"])
        self.assertNotIn("record_id", json.dumps(v["passages"]))
        with patch.object(N, "pack", return_value=RECORDS[:2]), self.assertRaises(RuntimeError):
            N.view(RUN)  # the rebuilt evidence must be what rx_r saw
        writer = {**RUN, "method": N.WRITER, "generation": {"hypothesis": "h", "supporting_evidence_ids": []}}
        with patch.object(N, "pack", return_value=RECORDS[:2]):
            self.assertEqual(len(N.view(writer)["passages"]), 2)

    def test_validate(self) -> None:
        out = N.validate(VALID)
        self.assertEqual((out["non_copying"], out["provenance"]["intervention"], out["provenance"]["mechanism"]),
                         (2, "P3", ""))
        for bad in ({**VALID, "non_copying": 0}, {**VALID, "non_copying": 6}, {**VALID, "non_copying": 2.5}, [], {}):
            self.assertIsNone(N.validate(bad))

    def test_judge_retries_and_payload_guard(self) -> None:
        replies = [{"non_copying": 9}, VALID]
        with patch.object(N, "call", side_effect=lambda j, u: replies.pop(0)):
            out = N.judge("deepseek", {"query": "q", "generation": {"hypothesis": "h"}, "passages": []})
        self.assertEqual((out["non_copying"], out["attempts"]), (2, 2))
        with self.assertRaises(N.H.TargetLeak):
            N.payload({"query": "q", "generation": {"hidden_target": 1}, "passages": []})

    def test_pairwise_prompt_replaces_only_criterion_4(self) -> None:
        self.assertNotEqual(N.PAIR_SYSTEM_V2, N.D.QUALITY_PAIR_SYSTEM)
        self.assertIn("go beyond the earlier work", N.PAIR_SYSTEM_V2)
        self.assertNotIn("well grounded", N.PAIR_SYSTEM_V2)
        self.assertEqual(N.PAIR_SYSTEM_V2.replace(N._NEW_4, N._OLD_4), N.D.QUALITY_PAIR_SYSTEM)

    def test_sp2(self) -> None:
        key = ("P", "broad", 1)
        rq = {key: {"scores": {"plausibility": 4, "testability": 4, "usefulness": 4}, "rq": 3.0}}
        with patch.object(N.Q, "rq_values", return_value=rq), patch.object(N, "load", return_value={key: {"non_copying": 2}}):
            self.assertEqual(N.sp2_values("m"), {key: 2.5})


if __name__ == "__main__":
    unittest.main()
