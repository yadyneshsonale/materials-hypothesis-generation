from __future__ import annotations

import unittest
from unittest.mock import patch

import hypo_loop as H
import loop_methods as LM

CASE = {"paper_id": "PMCT", "publication_date": "2024-06-01", "split": "validation",
        "queries": {"broad": {"text": "Improve the ductility of a refractory alloy."},
                    "problem_constrained": {"text": "Improve the ductility of as-cast HfNbTaTiZr at room temperature."},
                    "expert_context": {"text": "Earlier work tried annealing; improve ductility."}},
        "hidden_target": {"intervention": "Addition of 4.2 at.% chromium by vacuum arc melting to form a Laves network",
                          "mechanism": "crack deflection by a reticulated Laves phase network in the BCC matrix",
                          "material_initial_state": "HfNbTaTiZr"}}


class GuardTests(unittest.TestCase):
    def test_target_values_and_key_are_blocked(self) -> None:
        h = H.Harness(CASE, "problem_constrained", 1)
        with self.assertRaises(H.TargetLeak):
            h.guard({"notes": CASE["hidden_target"]["intervention"]})
        with self.assertRaises(H.TargetLeak):
            h.guard({"hidden_target": {}})
        h.guard({"q": h.query, "notes": "consider composition changes"})

    def test_ask_rejects_leaky_payload_before_calling(self) -> None:
        h = H.Harness(CASE, "broad", 1)
        with patch.object(H.lc, "trapi_chat_json") as call:
            with self.assertRaises(H.TargetLeak):
                h.ask("writer", "llama", "system", {"x": CASE["hidden_target"]["mechanism"]})
            call.assert_not_called()

    def test_ask_logs_role_and_pre_cutoff_model(self) -> None:
        h = H.Harness(CASE, "broad", 1)
        with patch.object(H.lc, "trapi_chat_json", return_value={"ok": True}):
            h.ask("framer", "o3mini", "system", {"q": h.query})
        self.assertEqual(h.models["framer"], "trapi:o3-mini_2025-01-31")
        self.assertEqual(h.trace[0]["role"], "framer")

    def test_only_pre_cutoff_models_are_registered(self) -> None:
        for spec in H.MODELS.values():
            self.assertIn(spec["deployment"], H.MODEL_CUTOFFS)


class SplitTests(unittest.TestCase):
    def test_test_split_requires_final(self) -> None:
        with self.assertRaises(SystemExit):
            H.generate_stage("closed_book", "test", 1, final=False)


class TournamentTests(unittest.TestCase):
    def test_consistent_both_order_wins_count_and_inconsistent_pairs_split(self) -> None:
        h = H.Harness(CASE, "broad", 1)
        cands = [{"hypothesis": f"c{i}"} for i in range(3)]

        def fake_ask(role, model, system, payload, max_out=None):  # candidate 0 always wins; 1 vs 2 position-biased
            a, b = payload["candidate_A"]["hypothesis"], payload["candidate_B"]["hypothesis"]
            if "c0" in (a, b):
                return {"winner": "A" if a == "c0" else "B"}
            return {"winner": "A"}

        with patch.object(h, "ask", side_effect=fake_ask):
            wins = LM.tournament(h, cands, "llama")
        self.assertEqual(wins, [2.0, 0.5, 0.5])


class DeterministicCheckTests(unittest.TestCase):
    def test_missing_numbers_and_baseline_are_flagged(self) -> None:
        problems = LM.deterministic_problems({"predicted_outcome": "ductility improves", "baseline": "",
                                             "falsification_experiment": {"falsification_rule": "if it fails"}}, {})
        self.assertEqual({p["field"] for p in problems}, {"predicted_outcome", "falsification_experiment", "baseline"})
        self.assertEqual(LM.deterministic_problems({"predicted_outcome": "+20% elongation", "baseline": "as-cast",
                                                    "falsification_experiment": {"falsification_rule": "< 5% gain"}},
                                                   {}), [])


if __name__ == "__main__":
    unittest.main()
