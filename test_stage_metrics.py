from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from stage_metrics import (
    ELEMENTS,
    _validated_audit,
    assert_target_free,
    check_composition_claim,
    icc1,
    kendall_tau,
    numbers_in,
    quantified_count,
    rom_density,
    traced_share,
    vec,
)


class PhysicsCheckTests(unittest.TestCase):
    def test_rule_of_mixtures_density_and_vec(self) -> None:
        equiatomic = {e: 0.2 for e in ("Hf", "Mo", "Ta", "Ti", "Zr")}
        # Measured HfMoTaTiZr density is about 10.4-10.5 g/cm^3; the rule of mixtures should land close.
        self.assertAlmostEqual(rom_density(equiatomic), 10.4, delta=0.4)
        self.assertAlmostEqual(vec(equiatomic), (4 + 6 + 5 + 4 + 4) / 5)
        self.assertAlmostEqual(vec({"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}), 8.0)

    def test_density_direction_check(self) -> None:
        claim = {"base": {"Hf": 20, "Nb": 20, "Ta": 20, "Ti": 20, "Zr": 20},
                 "modified": {"Hf": 20, "Mo": 20, "Ta": 20, "Ti": 20, "Zr": 20},
                 "claimed_density_change": "decrease", "claimed_phase": "unspecified"}
        # Replacing Nb (8.57) with Mo (10.28) raises density, so a claimed decrease is inconsistent.
        self.assertEqual(check_composition_claim(claim)["density"], "inconsistent")
        claim["claimed_density_change"] = "increase"
        self.assertEqual(check_composition_claim(claim)["density"], "consistent")

    def test_phase_check_uses_vec_rule_and_rejects_unknown_elements(self) -> None:
        fcc = {"modified": {"Co": 20, "Cr": 20, "Fe": 20, "Mn": 20, "Ni": 20}, "claimed_phase": "FCC"}
        self.assertEqual(check_composition_claim(fcc)["phase"], "consistent")
        fcc["claimed_phase"] = "BCC"
        self.assertEqual(check_composition_claim(fcc)["phase"], "inconsistent")
        unknown = {"modified": {"Xx": 50, "Ni": 50}, "claimed_phase": "FCC"}
        self.assertEqual(check_composition_claim(unknown)["phase"], "unverifiable")
        self.assertIn("Hf", ELEMENTS)


class TextMetricTests(unittest.TestCase):
    def test_numbers_and_tracing(self) -> None:
        text = "Add 4.2 at.% Cr and anneal at 1000 °C for 2 h; yield 1235.50 HV; Hf0.16 ignored"
        numbers = numbers_in(text)
        self.assertIn("4.2", numbers)
        self.assertIn("1000", numbers)
        self.assertIn("1235.5", numbers)
        self.assertNotIn("2", numbers)
        self.assertNotIn("0.16", numbers)
        self.assertAlmostEqual(traced_share(["4.2", "1000"], "measured 4.2 at.% at 900 °C"), 0.5)
        self.assertIsNone(traced_share([], "anything"))

    def test_quantified_count(self) -> None:
        self.assertEqual(quantified_count("4.2 at.% Cr, 1000 °C, 6 GPa, 2 h, 1235 HV"), 5)
        self.assertEqual(quantified_count("some samples were tested"), 0)


class StatisticsTests(unittest.TestCase):
    def test_icc_high_when_judgments_agree_and_low_when_random(self) -> None:
        agree = [[0, 0, 0], [1, 1, 1], [2, 2, 2], [3, 3, 3]]
        self.assertAlmostEqual(icc1(agree), 1.0)
        noisy = [[0, 3, 1], [3, 0, 2], [1, 2, 0], [2, 1, 3]]
        self.assertLess(icc1(noisy), 0.2)

    def test_kendall_tau(self) -> None:
        self.assertAlmostEqual(kendall_tau([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertAlmostEqual(kendall_tau([1, 2, 3], [3, 2, 1]), -1.0)


class SafetyAndValidationTests(unittest.TestCase):
    def test_target_free_guard(self) -> None:
        assert_target_free({"query": "q", "hypothesis": {}, "cited_evidence": []})
        with self.assertRaises(ValueError):
            assert_target_free({"query": "q", "hidden_target": {"intervention": "x"}})

    def test_audit_validation_clamps_and_defaults(self) -> None:
        audit = _validated_audit({
            "claims": [{"text": "c", "support": "weird", "same_system": "maybe", "needs_support": True,
                        "supporting_ids": ["A::c1", 3]}],
            "chain": {"intervention_to_mediator": 5, "mediator_to_mechanism": "x"},
            "mechanism_source": "bogus", "stated_uncertainty": "2",
            "falsifiability": {"threshold": True},
        })
        self.assertEqual(audit["claims"][0]["support"], "unsupported")
        self.assertEqual(audit["claims"][0]["same_system"], "unclear")
        self.assertEqual(audit["chain"], {"intervention_to_mediator": 2, "mediator_to_mechanism": 0,
                                          "mechanism_to_outcome": 0})
        self.assertEqual(audit["mechanism_source"], "not_from_evidence")
        self.assertEqual(audit["stated_uncertainty"], 2)
        self.assertTrue(audit["falsifiability"]["threshold"])
        self.assertFalse(audit["falsifiability"]["control"])
        self.assertEqual(_validated_audit(None)["claims"], [])

    def test_audit_stage_never_sends_hidden_target(self) -> None:
        import stage_metrics
        unit = {"key": "tool_agent__PMCX__broad", "arm": "tool_agent", "paper_id": "PMCX", "query": "q",
                "generation": {"hypothesis": "h", "supporting_evidence_ids": []}, "cited_ids": [],
                "cited_evidence": [], "judgment": {"recon": 1.0}}
        sent = {}

        def capture(system, user, max_tokens=8000, retries=6):
            sent["payload"] = json.loads(user)
            return {"claims": []}

        with patch.object(stage_metrics, "load_units", return_value=[unit]), \
                patch.object(stage_metrics, "load_replays", return_value={}), \
                patch.object(stage_metrics.lc, "judge_chat_json", side_effect=capture), \
                patch.object(stage_metrics, "atomic_json"):
            result = stage_metrics.audit_stage(workers=1, resume=False)
        self.assertEqual(result, {"done": 1, "failed": 0})
        self.assertEqual(set(sent["payload"]), {"query", "hypothesis", "cited_evidence"})


if __name__ == "__main__":
    unittest.main()
