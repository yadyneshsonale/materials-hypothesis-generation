"""Tests for experiment 43 (loop.md 24.1): the research-quality (RQ) judge and its validation checks."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import rq_judge as RQ

GEN = {"hypothesis": "Adding 5 at.% Al to HfNbTaTiZr forms an alumina scale.", "material_initial_state": "as cast",
       "intervention": "5 at.% Al", "conditions": "1000 C in air", "structural_mediator": "Al2O3 scale",
       "mechanism": "selective oxidation", "predicted_outcome": "lower mass gain", "baseline": "base alloy",
       "boundary": "while the scale is continuous", "uncertainty": "spallation",
       "supporting_evidence_ids": ["P1::web::001::results"], "conflicting_evidence_ids": [],
       "falsification_experiment": {"design": "oxidise both alloys", "measurements": ["mass gain"],
                                    "falsification_rule": "no lower mass gain"}}
VALID = {"plausibility_reason": "ok", "plausibility": 4, "testability_reason": "ok", "testability": 3,
         "usefulness_reason": "ok", "usefulness": 5}


class JudgeTests(unittest.TestCase):
    def test_validate(self) -> None:
        self.assertEqual(RQ.validate(VALID)["scores"], {"plausibility": 4, "testability": 3, "usefulness": 5})
        self.assertEqual(RQ.validate({**VALID, "testability": "3"})["scores"]["testability"], 3)
        for bad in ({**VALID, "usefulness": 6}, {**VALID, "plausibility": 0}, {**VALID, "testability": 3.5},
                    {k: v for k, v in VALID.items() if k != "usefulness"}, {**VALID, "plausibility": "high"}, []):
            self.assertIsNone(RQ.validate(bad))

    def test_rq_scale(self) -> None:
        self.assertAlmostEqual(RQ.rq({"plausibility": 4, "testability": 3, "usefulness": 5}), 3.0)
        self.assertAlmostEqual(RQ.rq({"plausibility": 1, "testability": 1, "usefulness": 1}), 0.0)

    def test_payload_is_the_expert_view(self) -> None:
        text = RQ.payload("How can oxidation be limited?", GEN)
        data = json.loads(text)
        self.assertEqual(data["research_question"], "How can oxidation be limited?")
        self.assertTrue(data["hypothesis"].startswith("- **Main hypothesis:**"))
        self.assertIn("Test that would falsify it", data["hypothesis"])
        self.assertNotIn("P1::web", text)
        with self.assertRaises(RQ.H.TargetLeak):
            RQ.payload("q", {**GEN, "hypothesis": "hidden_target leak"})

    def test_judge_retries_invalid_output(self) -> None:
        replies = [{"plausibility": 9}, VALID]
        with patch.object(RQ, "call", side_effect=lambda j, u: replies.pop(0)):
            out = RQ.judge("o1", "q", GEN)
        self.assertEqual(out["attempts"], 2)
        self.assertAlmostEqual(out["rq"], 3.0)
        with patch.object(RQ, "call", return_value={"plausibility": 9}):
            with self.assertRaises(RQ.lc.LLMError):
                RQ.judge("o1", "q", GEN)


class AnalysisTests(unittest.TestCase):
    def write(self, root: Path, kind: str, name: str, judge: str, item: str, scores: dict[str, int]) -> None:
        path = root / kind / name / judge / f"{item}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"item": item, "scores": scores, "rq": RQ.rq(scores)}))

    def test_validation_checks(self) -> None:
        good = {"plausibility": 5, "testability": 4, "usefulness": 5}
        by_control = {"positive": good, "hard_negative": good,
                      "random_negative": {"plausibility": 4, "testability": 4, "usefulness": 2},
                      "intervention_swap": {"plausibility": 3, "testability": 4, "usefulness": 4},
                      "mechanism_swap": {"plausibility": 4, "testability": 4, "usefulness": 4},
                      "generic": {"plausibility": 3, "testability": 2, "usefulness": 2}}
        with tempfile.TemporaryDirectory() as tmp, patch.object(RQ, "RQ_DIR", Path(tmp)):
            for n in range(36):
                for control, scores in by_control.items():
                    self.write(Path(tmp), "controls", "controls", "o1", f"PMC{n:03d}__{control}", scores)
            for n in range(135):
                s = {"plausibility": 1 + n % 5, "testability": 1 + n % 5, "usefulness": 1 + n % 5}
                self.write(Path(tmp), "runs", RQ.WRITER, "o1", f"PMC{n:03d}__broad__w__s1", s)
                self.write(Path(tmp), "retest", RQ.WRITER, "o1", f"PMC{n:03d}__broad__w__s1", s)
            v = RQ.validation("o1")
        self.assertTrue(v["controls_complete"])
        self.assertEqual(v["gaps"]["usefulness_positive_minus_random"], 3.0)
        self.assertTrue(v["checks"]["C1_relevance_usefulness_gap_ge_1"])
        self.assertTrue(v["checks"]["C2_specificity_rq_gap_ge_1"])
        self.assertTrue(v["checks"]["C3_consistency_plausibility_gaps_ge_0.5"])  # gaps 2.0 and 1.0
        self.assertTrue(v["checks"]["C4_retest_rho_ge_0.80"])
        self.assertTrue(v["internally_validated"])
        self.assertEqual(v["retest"]["pairs"], 135)

    def test_failed_consistency_and_retest(self) -> None:
        flat = {"plausibility": 4, "testability": 4, "usefulness": 4}
        with tempfile.TemporaryDirectory() as tmp, patch.object(RQ, "RQ_DIR", Path(tmp)):
            for n in range(36):
                for control in RQ.RM.CONTROLS:
                    self.write(Path(tmp), "controls", "controls", "deepseek", f"PMC{n:03d}__{control}", flat)
            v = RQ.validation("deepseek")
        self.assertFalse(v["checks"]["C1_relevance_usefulness_gap_ge_1"])
        self.assertFalse(v["checks"]["C3_consistency_plausibility_gaps_ge_0.5"])
        self.assertFalse(v["checks"]["C4_retest_rho_ge_0.80"])
        self.assertFalse(v["internally_validated"])

    def test_three_call_mean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.object(RQ, "RQ_DIR", Path(tmp)):
            for rep, u in ((1, 2), (2, 3), (3, 5)):
                self.write(Path(tmp), RQ.rep_kind("runs", rep), "m", "deepseek", "PMC1__broad__m__s1",
                           {"plausibility": 4, "testability": 4, "usefulness": u})
            self.write(Path(tmp), "runs", "m", "deepseek", "PMC2__broad__m__s1",
                       {"plausibility": 4, "testability": 4, "usefulness": 4})  # one call only: dropped at k=3
            three = RQ.load("runs", "m", "deepseek", 3)
            one = RQ.load("runs", "m", "deepseek")
        self.assertEqual(sorted(three), ["PMC1__broad__m__s1"])
        self.assertAlmostEqual(three["PMC1__broad__m__s1"]["scores"]["usefulness"], 10 / 3)
        self.assertAlmostEqual(three["PMC1__broad__m__s1"]["rq"], (4 + 4 + 10 / 3) / 3 - 1)
        self.assertEqual(len(one), 2)
        self.assertEqual(RQ.rep_kind("retest", 1), "retest")
        self.assertEqual(RQ.rep_kind("retest", 3), "retest_rep3")

    def test_run_stage_resumes_and_writes_once(self) -> None:
        items = [("runs", "m", f"PMC00{i}__broad__m__s1", {"query": "q", "generation": GEN}) for i in range(3)]
        with tempfile.TemporaryDirectory() as tmp, patch.object(RQ, "RQ_DIR", Path(tmp)), \
                patch.object(RQ, "call", return_value=VALID):
            self.write(Path(tmp), "runs", "m", "o1", "PMC000__broad__m__s1",
                       {"plausibility": 1, "testability": 1, "usefulness": 1})
            counts = RQ.run_stage(items, "o1", 2)
            kept = json.loads((Path(tmp) / "runs" / "m" / "o1" / "PMC000__broad__m__s1.json").read_text())
            new = json.loads((Path(tmp) / "runs" / "m" / "o1" / "PMC001__broad__m__s1.json").read_text())
        self.assertEqual(counts, {"jobs": 2, "done": 2, "failed": 0})
        self.assertEqual(kept["rq"], 0.0)
        self.assertEqual(new["scores"], {"plausibility": 4, "testability": 3, "usefulness": 5})
        self.assertEqual(new["judge"], "o1")


if __name__ == "__main__":
    unittest.main()
