from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import hypo_loop as H
import loop_final as LF
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


def _row(method: str, split: str, paper: str, level: str, score: int) -> dict:
    run = {"method": method, "split": split, "paper_id": paper, "query_level": level, "status": "ok",
           "generation": {"hypothesis": "h", "predicted_outcome": "o"}, "llm_calls": 1, "chars_in": 10,
           "elapsed_seconds": 1.0, "models": {"writer": "trapi:x"}, "run_id": f"{paper}__{level}__{method}"}
    return {"run": run, "gpt": {"scores": {d: score for d in H.ALL_DIMENSIONS}}, "deep": None, "audit": None,
            "label": None}


class ReportTests(unittest.TestCase):
    def test_test_and_all_reports_only_include_methods_run_on_those_splits(self) -> None:
        rows = [_row("closed_book", s, p, "broad", 1) for s, p in (("dev", "D1"), ("test", "T1"))]
        rows += [_row("dev_only_method", "dev", "D1", "broad", 2)]
        with tempfile.TemporaryDirectory() as tmp, patch.object(H, "OUT", Path(tmp)), \
                patch.object(H, "load_scored", return_value=rows):
            self.assertEqual(set(H.report("dev")["table"]), {"closed_book", "dev_only_method"})
            self.assertEqual(set(H.report("test")["table"]), {"closed_book"})
            self.assertEqual(set(H.report("all")["table"]), {"closed_book"})


class SpearmanTests(unittest.TestCase):
    def test_ranks_average_ties(self) -> None:
        self.assertEqual(LF._ranks([1.0, 2.0, 2.0, 3.0]), [1.0, 2.5, 2.5, 4.0])

    def test_monotone_reversed_and_constant(self) -> None:
        self.assertEqual(LF.spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertEqual(LF.spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertIsNone(LF.spearman([1, 2, 3], [5, 5, 5]))


class NicheTests(unittest.TestCase):
    QUESTION = ("Earlier studies examined room-temperature wear but largely addressed a limited thermal regime "
                "rather than the response across different temperatures. What governs wear resistance?")

    def test_only_verbatim_quotes_survive(self) -> None:
        raw = {"niches": [{"quote": "largely addressed a limited thermal regime rather than the response",
                           "kind": "untested_condition"},
                          {"quote": "earlier work never linked pre-oxidation to wear", "kind": "method_limitation"},
                          {"quote": "Largely  addressed a limited thermal regime rather than the response.",
                           "kind": "untested_condition"}]}
        kept = LM.verified_niches(self.QUESTION, raw)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["kind"], "untested_condition")

    def test_no_verified_niche_falls_back_to_the_question(self) -> None:
        kept = LM.verified_niches(self.QUESTION, {"niches": [{"quote": "an invented gap", "kind": "x"}]})
        self.assertEqual(kept, [{"quote": LM._norm(self.QUESTION), "kind": "open_question"}])


class Bm25PackTests(unittest.TestCase):
    def test_budget_cap_and_seen_are_respected(self) -> None:
        from temporal_hypothesis_benchmark import RetrievalRecord
        pool = [RetrievalRecord(f"r{i}", "P1", "2020-01-01", "chunk", ("tungsten " if i % 3 == 0 else "") +
                                "alloy " * 400, {}) for i in range(30)]
        h = H.Harness(CASE, "broad", 1)
        with patch.object(h, "pool", return_value=pool):
            packed = LM.pack_bm25(h, "tungsten alloy")
        self.assertTrue(packed and all("tungsten" in r.text for r in packed[:3]))
        self.assertLessEqual(sum(min(len(r.text), LM.rx.record_cap("text_chunks")) for r in packed),
                             LM.rx.EVIDENCE_BUDGET_CHARS)
        self.assertLessEqual(len(packed), LM.rx.MAX_RECORDS)
        self.assertTrue(all(r.record_id in h.seen for r in packed))


class Test2SplitTests(unittest.TestCase):
    def test_held_out_splits_need_final_and_all_excludes_test2(self) -> None:
        for split in ("test", "test2", "all"):
            with self.assertRaises(SystemExit):
                H.generate_stage("closed_book", split, 1, final=False)
        self.assertEqual(H.SPLITS["all"], {"dev", "test"})
        self.assertEqual(H.split_of({"split": "test2"}), "test2")
        self.assertEqual(H.split_of({"split": "validation"}), "dev")


if __name__ == "__main__":
    unittest.main()
