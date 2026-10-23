from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import improvement_eval as ie
from temporal_hypothesis_benchmark import RetrievalRecord


def _gen(supporting: list[str] | None = None, hypothesis: str = "Add Cr to raise strength.") -> dict:
    return {"hypothesis": hypothesis, "material_initial_state": "HfMoTaTiZr", "intervention": "Add 4 at.% Cr",
            "conditions": "RT", "structural_mediator": "Laves", "mechanism": "SSH", "predicted_outcome": "+10%",
            "baseline": "HfMoTaTiZr", "boundary": "<5%", "uncertainty": "", "supporting_evidence_ids": supporting or [],
            "conflicting_evidence_ids": [], "falsification_experiment": {"design": "d", "measurements": [],
                                                                          "falsification_rule": "r"}}


CASE = {"paper_id": "PMCT", "publication_date": "2024-01-02",
        "queries": {"broad": {"text": "q broad"}, "problem_constrained": {"text": "q pc"},
                    "expert_context": {"text": "q ec"}},
        "hidden_target": {"intervention": "secret"}}


class PromptTests(unittest.TestCase):
    def test_closed_book_fixed_allows_own_knowledge_and_has_no_evidence_only_rule(self) -> None:
        self.assertIn("use your own knowledge", ie.CLOSED_BOOK_FIXED_SYSTEM)
        self.assertNotIn("Use ONLY the supplied", ie.CLOSED_BOOK_FIXED_SYSTEM)
        self.assertIn('"hypothesis"', ie.CLOSED_BOOK_FIXED_SYSTEM)

    def test_systemmatch_requires_appraisal_before_hypothesis(self) -> None:
        text = ie.SYSTEMMATCH_SYSTEM
        self.assertLess(text.index("evidence_appraisal"), text.index('"hypothesis"'))
        self.assertIn("does_not_transfer", text)

    def test_knowledge_first_keeps_draft_mechanism(self) -> None:
        self.assertIn("Do not replace the mechanism", ie.KNOWLEDGE_FIRST_SYSTEM)


class GenerationTests(unittest.TestCase):
    def test_generate_validated_repairs_once(self) -> None:
        replies = [{"hypothesis": ""}, _gen(["A::c1"])]
        with patch.object(ie.lc, "chat_json", side_effect=replies) as call:
            out = ie.generate_validated("sys", {"query": "q"}, {"A::c1"})
        self.assertEqual(call.call_count, 2)
        self.assertEqual(out["citation_validation"]["status"], "valid_after_regeneration")
        self.assertEqual(out["supporting_evidence_ids"], ["A::c1"])
        repair_payload = json.loads(call.call_args_list[1].args[1])
        self.assertIn("validation_error", repair_payload)

    def test_generate_validated_raises_when_repair_still_invalid(self) -> None:
        with patch.object(ie.lc, "chat_json", side_effect=[_gen(["X"]), _gen(["Y"])]):
            with self.assertRaises(ValueError):
                ie.generate_validated("sys", {"query": "q"}, {"A::c1"})

    def test_closed_book_fixed_payload_has_no_evidence_or_target(self) -> None:
        sent = {}

        def capture(system, user, max_tokens=4000, retries=3):
            sent["system"], sent["payload"] = system, json.loads(user)
            return _gen()

        with tempfile.TemporaryDirectory() as tmp, patch.object(ie, "OUT", Path(tmp)), \
                patch.object(ie.lc, "chat_json", side_effect=capture), \
                patch.object(ie.rx, "metadata", return_value={"PMCT": {"work_family_id": "f"}}):
            ie.generate_one(CASE, "broad", "closed_book_fixed", 1)
            run = json.loads((Path(tmp) / "runs" / "PMCT__broad__closed_book_fixed__s1.json").read_text())
        self.assertEqual(set(sent["payload"]), {"query", "knowledge_cutoff"})
        self.assertEqual(sent["system"], ie.CLOSED_BOOK_FIXED_SYSTEM)
        self.assertEqual(run["status"], "ok")
        self.assertEqual(run["packed_ids"], [])

    def test_knowledge_first_fails_cleanly_without_a_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.object(ie, "OUT", Path(tmp)), \
                patch.object(ie.rx, "metadata", return_value={"PMCT": {"work_family_id": "f"}}):
            (Path(tmp) / "runs").mkdir()
            (Path(tmp) / "runs" / "PMCT__broad__closed_book_fixed__s1.json").write_text(
                json.dumps({"run_id": "PMCT__broad__closed_book_fixed__s1", "status": "failed", "generation": None}))
            ie.generate_one(CASE, "broad", "knowledge_first", 1)
            run = json.loads((Path(tmp) / "runs" / "PMCT__broad__knowledge_first__s1.json").read_text())
        self.assertEqual(run["status"], "failed")
        self.assertIn("draft", run["error"])

    def test_evidence_for_matches_experiment_14_packing(self) -> None:
        pool = [RetrievalRecord(f"P{i}::r", f"P{i}", "2020-01-01", "chunk", "chromium laves " + "x" * 1500, {})
                for i in range(30)]
        with patch.object(ie.rx, "case_pool", return_value=(set(), pool)):
            packed = ie.evidence_for({**CASE, "queries": {"broad": {"text": "chromium laves"}}}, "broad", "text_chunks")
        self.assertEqual([r.record_id for r in packed],
                         [r.record_id for r in ie.rx.pack("chromium laves", pool, ie.rx.record_cap("text_chunks"))])


class SelectionTests(unittest.TestCase):
    def _runs(self) -> dict:
        runs = {}
        for i, arm in enumerate(ie.ENSEMBLE_POOL):
            runs[ie.run_id("PMCT", "broad", arm, 1)] = {"status": "ok", "generation": _gen(hypothesis=f"hyp {i}")}
        return runs

    def test_selector_is_blinded_deterministic_and_target_free(self) -> None:
        sent = {}

        def capture(system, user, max_tokens=2000, retries=3):
            sent["payload"] = user
            return {"choice": "C2", "reason": "r"}

        with tempfile.TemporaryDirectory() as tmp, patch.object(ie, "OUT", Path(tmp)), \
                patch.object(ie.lc, "chat_json", side_effect=capture):
            ie.select_one(CASE, "broad", 1, self._runs())
            sel = json.loads((Path(tmp) / "selections" / "PMCT__broad__ensemble_select__s1.json").read_text())
        for arm in ie.ENSEMBLE_POOL:
            self.assertNotIn(arm, sent["payload"])
        self.assertNotIn("secret", sent["payload"])
        self.assertNotIn("hidden_target", sent["payload"])
        self.assertEqual(sel["chosen_arm"], sel["labels"]["C2"])
        self.assertFalse(sel["fallback"])
        order = ie.candidate_order("PMCT", "broad", 1, list(ie.ENSEMBLE_POOL))
        self.assertEqual(order, ie.candidate_order("PMCT", "broad", 1, list(ie.ENSEMBLE_POOL)))
        self.assertEqual(list(sel["labels"].values()), order)

    def test_ordinary_words_containing_card_do_not_trip_the_leak_check(self) -> None:
        runs = self._runs()
        runs[ie.run_id("PMCT", "broad", "card", 1)]["generation"] = _gen(hypothesis="Discarded phases were removed.")
        with tempfile.TemporaryDirectory() as tmp, patch.object(ie, "OUT", Path(tmp)), \
                patch.object(ie.lc, "chat_json", return_value={"choice": "C1"}):
            ie.select_one(CASE, "broad", 1, runs)
            self.assertTrue((Path(tmp) / "selections" / "PMCT__broad__ensemble_select__s1.json").exists())

    def test_invalid_choice_falls_back_and_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.object(ie, "OUT", Path(tmp)), \
                patch.object(ie.lc, "chat_json", return_value={"choice": "C99"}):
            ie.select_one(CASE, "broad", 1, self._runs())
            sel = json.loads((Path(tmp) / "selections" / "PMCT__broad__ensemble_select__s1.json").read_text())
        self.assertTrue(sel["fallback"])
        self.assertEqual(sel["choice"], "C1")


class AnalysisHelperTests(unittest.TestCase):
    def test_unit_scores_average_samples_and_filter_levels(self) -> None:
        scores = lambda v: {"scores": {d: v for d in ie.PRIMARY_DIMENSIONS}}  # noqa: E731
        records = {
            ("P", "broad", "a", 1): {"gpt": scores(1)}, ("P", "broad", "a", 2): {"gpt": scores(3)},
            ("P", "expert_context", "a", 1): {"gpt": scores(4)}, ("P", "broad", "b", 1): {"gpt": scores(0)},
        }
        self.assertEqual(ie.unit_scores(records, "a", "gpt"), {("P", "broad"): 2.0, ("P", "expert_context"): 4.0})
        self.assertEqual(ie.unit_scores(records, "a", "gpt", ("expert_context",)), {("P", "expert_context"): 4.0})

    def test_representation_mapping(self) -> None:
        self.assertEqual(ie.representation_of("knowledge_first"), "text_chunks")
        self.assertEqual(ie.representation_of("card_systemmatch"), "card")
        self.assertIsNone(ie.representation_of("closed_book_fixed"))


if __name__ == "__main__":
    unittest.main()
