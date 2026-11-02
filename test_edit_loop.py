"""Tests for experiment 45 (loop.md 26.1): the lever-preserving editor and the domain context (edit_loop.py), and the
composition of the arms in the analysis (edit_experiment.py). No API calls: every model answer is faked."""

from __future__ import annotations

import os
import random
import unittest
from typing import Any
from unittest.mock import patch

import edit_loop as EL
from temporal_hypothesis_benchmark import RetrievalRecord


def rec(pid: str, n: int, text: str) -> RetrievalRecord:
    return RetrievalRecord(f"{pid}::web::{n:03d}::results", pid, "2020-01-01", "web:Results", text,
                           {"source": "web", "title": "T", "dates": {"crossref": "2020-01-01"}})


RECORDS = [rec("P1", 1, "Cr additions of 5 at.% refined the Laves phase."), rec("P2", 2, "Unrelated passage.")]
DRAFT = {"hypothesis": "Adding 4 at.% Cr to HfMoTaTiZr lowers density.", "material_initial_state": "As-cast HfMoTaTiZr",
         "intervention": "Add 4 at.% Cr to HfMoTaTiZr by arc melting", "conditions": "Compression at 1000 C for 2 h",
         "structural_mediator": "About 4 vol% Laves phase", "mechanism": "Solid-solution strengthening",
         "predicted_outcome": "Density falls by 3%", "baseline": "As-cast HfMoTaTiZr", "boundary": "Below 1200 C",
         "uncertainty": "Laves morphology", "supporting_evidence_ids": [RECORDS[0].record_id],
         "conflicting_evidence_ids": [], "falsification_experiment": {"design": "d", "measurements": ["m"],
                                                                      "falsification_rule": "r"}}


class FakeHarness:
    def __init__(self, query: str, answers: list[Any]) -> None:
        self.query, self.cutoff, self.level, self.sample = query, "2024-06-01", "broad", 1
        self.case = {"paper_id": "PMCX"}
        self.rng = random.Random(1)
        self.seen: dict[str, RetrievalRecord] = {}
        self.notes: dict[str, Any] = {}
        self.models: dict[str, str] = {}
        self.trace: list[dict[str, Any]] = []
        self.answers = list(answers)
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.source = "web"

    def ask(self, role: str, model: str, system: str, payload: dict[str, Any], max_out: int | None = None) -> Any:
        self.calls.append((role, payload))
        return self.answers.pop(0)

    def generate_final(self, role: str, model: str, system: str, payload: dict[str, Any], allowed: set[str],
                       citation_repair: str = "regenerate") -> dict[str, Any]:
        self.calls.append((role, payload))
        return {"hypothesis": "h", "citation_validation": {"status": "valid"}}


def fake_pack(h: Any, focused: bool, budget: int) -> list[RetrievalRecord]:
    for r in RECORDS:
        h.seen[r.record_id] = r
    return list(RECORDS)


def base_run() -> dict[str, Any]:
    return {"run_id": "PMCX__broad__rx_base__s1", "status": "ok", "llm_calls": 1, "chars_in": 100,
            "seen_ids": sorted(r.record_id for r in RECORDS), "models": {"writer": "trapi:o3-mini_2025-01-31"},
            "generation": {**DRAFT, "citation_validation": {"status": "valid", "removed_unknown_ids": []}}}


class HelperTests(unittest.TestCase):
    def test_names_alloy_class(self) -> None:
        for q in ("For refractory high-entropy alloys, ...", "In MPEAs ...", "multi-principal element alloys",
                  "a medium-entropy alloy", "HEA coatings"):
            self.assertTrue(EL.names_alloy_class(q), q)
        for q in ("As-cast HfMoTaTiZr has high strength", "an elemental Cr coating on a Zr-alloy cladding"):
            self.assertFalse(EL.names_alloy_class(q), q)

    def test_elements(self) -> None:
        self.assertEqual(EL.elements("Cr2(Ti,Zr,Hf,Ta) Laves in HfMoTaTiZr; Al2O3; BCC/B2; TEM; The"),
                         {"Cr", "Ti", "Zr", "Hf", "Ta", "Mo", "Al"})
        self.assertEqual(EL.elements("a minor chromium addition"), {"Cr"})

    def test_lever_check(self) -> None:
        ok = EL.lever_check(DRAFT, {"intervention": "Add a minor amount of Cr to HfMoTaTiZr by arc melting"}, "q")
        self.assertTrue(ok["ok"])
        swap = EL.lever_check(DRAFT, {"intervention": "Add a minor amount of V to HfMoTaTiZr by arc melting"}, "q")
        self.assertFalse(swap["ok"])
        self.assertEqual((swap["dropped"], swap["added"]), (["Cr"], ["V"]))
        coating = {"intervention": "Anneal the coating in flowing argon after plasma spraying"}
        vague = EL.lever_check(coating, {"intervention": "Change the coating heat treatment"}, "q")
        self.assertFalse(vague["ok"])
        self.assertIn("content words", vague["problem"])
        # An element the question names is not a new lever.
        named = EL.lever_check(DRAFT, {"intervention": "Add a minor amount of Cr to HfMoTaTiZr by arc melting, as "
                                                        "with Nb"}, "Nb-bearing alloys")
        self.assertTrue(named["ok"])

    def test_apply_edit_changes_only_editable_fields(self) -> None:
        raw = {**DRAFT, "intervention": "Add a minor amount of Cr to HfMoTaTiZr by arc melting",
               "predicted_outcome": "Density falls by 9%", "supporting_evidence_ids": ["made-up"],
               "falsification_experiment": {"design": "other"}}
        edited, check = EL.apply_edit(DRAFT, {"draft_hypothesis": raw}, "q")
        self.assertTrue(check["ok"])
        self.assertEqual(check["changed"], ["intervention"])
        for field in ("predicted_outcome", "supporting_evidence_ids", "falsification_experiment"):
            self.assertEqual(edited[field], DRAFT[field])

    def test_numbers_outside(self) -> None:
        self.assertEqual(EL.numbers_outside("Add 4 at.% Cr at 1000 C", "the question names 1000 C"), 1)


class EditTests(unittest.TestCase):
    def run_edit(self, answers: list[Any], query: str = "How can HfMoTaTiZr be made lighter at 1000 C?"
                 ) -> tuple[dict[str, Any], FakeHarness]:
        h = FakeHarness(query, answers)
        with patch.object(EL, "stage1_run", return_value=base_run()), patch.object(EL.RL, "start_pack", fake_pack):
            out = EL.m_edit(h, "rx_base", focused=False)
        return out, h

    def test_edit_applied_keeps_ids_and_records_numbers(self) -> None:
        good = {**DRAFT, "intervention": "Add a minor amount of Cr to HfMoTaTiZr by arc melting",
                "conditions": "Compression at the service temperature the question names"}
        out, h = self.run_edit([good])
        self.assertEqual(out["intervention"], good["intervention"])
        self.assertEqual(out["supporting_evidence_ids"], DRAFT["supporting_evidence_ids"])
        self.assertEqual(out["citation_validation"]["status"], "valid")
        self.assertTrue(h.notes["edit"]["applied"])
        self.assertEqual(h.notes["edit"]["invented_numbers_before"]["intervention"], 1)  # 4 at.%: not in the sources
        self.assertEqual(h.notes["edit"]["invented_numbers_before"]["conditions"], 1)  # 2 h; 1000 is in the question
        self.assertEqual(h.notes["edit"]["invented_numbers_after"]["conditions"], 0)
        self.assertEqual(h.notes["stage1"]["run_id"], "PMCX__broad__rx_base__s1")
        self.assertEqual(h.models["writer"], "trapi:o3-mini_2025-01-31")
        role, payload = h.calls[0]
        self.assertEqual(sorted(payload), ["cited_evidence", "draft_hypothesis", "knowledge_cutoff", "query"])
        self.assertEqual([i["record_id"] for i in payload["cited_evidence"]], [RECORDS[0].record_id])

    def test_lever_change_is_retried_then_falls_back_to_the_draft(self) -> None:
        swap = {**DRAFT, "intervention": "Add a minor amount of V to HfMoTaTiZr by arc melting"}
        out, h = self.run_edit([swap, swap])
        self.assertEqual(out["intervention"], DRAFT["intervention"])
        self.assertFalse(h.notes["edit"]["applied"])
        self.assertEqual([c[0] for c in h.calls], ["editor", "editor_retry"])
        self.assertIn("dropped Cr", h.calls[1][1]["instruction"])

    def test_retry_can_succeed(self) -> None:
        swap = {**DRAFT, "intervention": "Add a minor amount of V to HfMoTaTiZr by arc melting"}
        good = {**DRAFT, "intervention": "Add a minor amount of Cr to HfMoTaTiZr by arc melting"}
        out, h = self.run_edit([swap, good])
        self.assertEqual(out["intervention"], good["intervention"])
        self.assertTrue(h.notes["edit"]["applied"])

    def test_pack_must_match_stage1(self) -> None:
        h = FakeHarness("q", [])
        run = {**base_run(), "seen_ids": ["other"]}
        with patch.object(EL, "stage1_run", return_value=run), patch.object(EL.RL, "start_pack", fake_pack):
            with self.assertRaises(RuntimeError):
                EL.m_edit(h, "rx_base", focused=False)


class DomainTests(unittest.TestCase):
    def test_domain_context_only_where_the_class_is_not_named(self) -> None:
        h = FakeHarness("What coating stops Cr-Zr interdiffusion on Zr-alloy cladding?", [])
        with patch.object(EL.RL, "start_pack", fake_pack):
            EL.m_domain(h, focused=True)
        payload = h.calls[0][1]
        self.assertEqual(payload["research_context"], EL.DOMAIN_CONTEXT)
        self.assertEqual(list(payload), ["query", "knowledge_cutoff", "research_context", "analysis_notes",
                                         "eligible_evidence"])
        with patch.object(EL.RL, "start_pack", fake_pack), self.assertRaises(RuntimeError):
            EL.m_domain(FakeHarness("Which high-entropy alloy ...?", []), focused=True)


class ComposeTests(unittest.TestCase):
    def test_compose_takes_named_units_from_the_first_source(self) -> None:
        import rq_judge as RQ

        with patch.dict(os.environ), patch.dict(RQ.ROOTS):
            import edit_experiment as EX

            named = {("P1", "broad"): True, ("P1", "expert_context"): False}
            data = {"rx_base": {("P1", "broad", 1): 1.0, ("P1", "expert_context", 1): 2.0},
                    "domain_rx_base": {("P1", "expert_context", 1): 3.0},
                    "edit_rx_base": {("P1", "broad", 1): 1.5, ("P1", "expert_context", 1): 2.5},
                    "domain_edit_rx_base": {("P1", "expert_context", 1): 3.5}}
            with patch.object(EX, "named_units", return_value=named):
                self.assertEqual(EX.compose("rx_base", "D", data.__getitem__),
                                 {("P1", "broad", 1): 1.0, ("P1", "expert_context", 1): 3.0})
                self.assertEqual(EX.compose("rx_base", "DE", data.__getitem__),
                                 {("P1", "broad", 1): 1.5, ("P1", "expert_context", 1): 3.5})
                d = EX.contrast(EX.compose("rx_base", "D", data.__getitem__),
                                EX.compose("rx_base", "base", data.__getitem__), "unnamed")
                self.assertEqual((d["runs"], d["diff"]), (1, 1.0))
            self.assertEqual(EX.per_paper({("P", "a", 1): 1.0, ("P", "a", 2): 3.0, ("P", "b", 1): 4.0},
                                          [("P", "a", 1), ("P", "a", 2), ("P", "b", 1)]), {"P": 3.0})


if __name__ == "__main__":
    unittest.main()
