"""Tests for the experiment-39 diagnostics (loop.md 20.1): oracle labelling, the guard, must_obey_check --oracle,
the reader, the copying measure and the pairwise scoring."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import diag_analysis as D
import hypo_loop as H
import loop_methods as LM
import must_obey_check as M
from temporal_hypothesis_benchmark import RetrievalRecord

KEY = {"material_initial_state": "cast HfNbTaTiZr refractory high-entropy alloy in the as-cast condition",
       "intervention": "Ink-extrusion three-dimensional printing followed by a slurry silicide coating cured in vacuum",
       "structural_mediator": "a continuous silicide layer that forms a self-healing mixed oxide during exposure",
       "mechanism": "the self-healing mixed oxide grown from the silicide coating blocks inward oxygen diffusion"}
CASE = {"paper_id": "PMCT", "publication_date": "2024-06-01", "split": "validation",
        "queries": {lvl: {"text": "Improve the oxidation resistance of a refractory high-entropy alloy."}
                    for lvl in ("broad", "problem_constrained", "expert_context")},
        "hidden_target": KEY}


def pool(kind: str) -> list[RetrievalRecord]:
    words = ("silicide coating oxygen", "aluminide pack cementation", "chromia scale growth", "zirconia barrier")
    return [RetrievalRecord(f"P{i}::web::{j:03d}::results", f"P{i}", "2020-01-01", "web:Results", f"{w} " * 60,
                            {"source": "web"}) for i, w in enumerate(words) for j in range(6)]


class Responder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, role, model, system, payload, max_out=None):
        self.calls.append((role, payload))
        if role == "reader":
            return {"approaches": [{"approach": "silicide coating", "material": "Nb alloys", "result": "lower mass gain",
                                    "limitation": "cracking", "record_ids": ["P0::web::000::results"]}],
                    "chosen_family": "surface_or_coating", "lever": "silicide coating", "why": "it blocks oxygen"}
        return {"hypothesis": "A coating protects the alloy.", "intervention": "coating", "mechanism": "oxide scale",
                "supporting_evidence_ids": [], "conflicting_evidence_ids": []}


def run(method: str, responder: Responder, hints: Path | None = None) -> H.Harness:
    h = H.Harness(CASE, "broad", 1)
    with patch.object(h, "pool", side_effect=pool), patch.object(H.Harness, "ask", autospec=True,
                                                                 side_effect=lambda self, *a, **k: responder(*a, **k)), \
            patch.object(LM, "ORACLE_HINTS", hints or LM.ORACLE_HINTS):
        H.METHODS[method](h)
    return h


class OracleMethodTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.hints = Path(self.tmp.name) / "hints.json"
        self.hints.write_text(json.dumps({"PMCT": {"class": "surface_or_coating", "lever": "a silicide coating"}}))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_registered(self) -> None:
        for method in LM.DIAG_CONFIGS:
            self.assertIn(method, H.METHODS)

    def test_targetpack_retrieves_with_the_key_and_keeps_the_guard(self) -> None:
        responder = Responder()
        h = run("oracle_targetpack_b_o3mini", responder)
        self.assertEqual(h.notes["oracle_diagnostic"], "target_selected_evidence")
        self.assertEqual(h.source, "web")
        self.assertTrue(h._forbidden)  # the payload guard stays on: only the selection uses the key
        evidence = responder.calls[-1][1]["eligible_evidence"]
        self.assertTrue(evidence)
        self.assertTrue(all(e["record_id"].startswith("P0::") for e in evidence[:6]))  # silicide passages first

    def test_question_pack_reader_is_target_free(self) -> None:
        responder = Responder()
        h = run("read_web_chunks_b_o3mini", responder)
        self.assertNotIn("oracle_diagnostic", h.notes)
        self.assertEqual([c[0] for c in responder.calls], ["reader", "writer"])
        self.assertEqual(responder.calls[1][1]["analysis_notes"]["lever"], "silicide coating")
        self.assertEqual(h.notes["reading"]["chosen_family"], "surface_or_coating")

    def test_hints_are_nested(self) -> None:
        r1, r2, r3 = Responder(), Responder(), Responder()
        run("oracle_hint_class_b_o3mini", r1, self.hints)
        run("oracle_hint_lever_b_o3mini", r2, self.hints)
        h = run("oracle_hint_full_b_o3mini", r3, self.hints)
        n1, n2, n3 = (r.calls[-1][1]["analysis_notes"] for r in (r1, r2, r3))
        self.assertEqual(n1["chosen_family"], "surface_or_coating")
        self.assertNotIn("lever", n1)
        self.assertEqual(n2["lever"], "a silicide coating")
        self.assertEqual(n3["collaborator_plan"]["intervention"], KEY["intervention"])
        self.assertEqual(h._forbidden, [])

    def test_full_hint_would_trip_the_guard_without_the_declared_exception(self) -> None:
        h = H.Harness(CASE, "broad", 1)
        with self.assertRaises(H.TargetLeak):
            h.guard({"notes": {"plan": KEY["intervention"]}})

    def test_generate_one_records_oracle_runs_honestly(self) -> None:
        responder = Responder()
        case = H.cases()["PMC10759803"]  # a real case: the leakage audit looks the paper up (no LLM call is made)
        self.hints.write_text(json.dumps({"PMC10759803": {"class": "composition_change", "lever": "Cr addition"}}))
        with tempfile.TemporaryDirectory() as tmp, patch.object(H, "OUT", Path(tmp)), \
                patch.object(H.Harness, "ask", autospec=True, side_effect=lambda self, *a, **k: responder(*a, **k)), \
                patch.object(LM, "ORACLE_HINTS", self.hints):
            H.generate_one("oracle_hint_full_b_o3mini", case, "broad", 1, False)
            H.generate_one("writer_only_b_o3mini", case, "broad", 1, False)
            oracle = json.loads(next(Path(tmp, "oracle_hint_full_b_o3mini", "runs").glob("*.json")).read_text())
            normal = json.loads(next(Path(tmp, "writer_only_b_o3mini", "runs").glob("*.json")).read_text())
        self.assertEqual(oracle["status"], "ok")
        self.assertIs(oracle["target_free_asserted"], False)
        self.assertEqual(oracle["oracle_diagnostic"], "hint_full_answer_key")
        self.assertIs(normal["target_free_asserted"], True)
        self.assertNotIn("oracle_diagnostic", normal)


class OracleCheckTests(unittest.TestCase):
    def write_run(self, root: Path, directory: str, oracle: bool) -> Path:
        case = json.loads(next((M.CASES).glob("PMC10759803.json")).read_text())
        query = case["queries"]["broad"]["text"]
        rid = f"PMC10759803__broad__{directory}__s1"
        run_dir = root / directory
        (run_dir / "runs").mkdir(parents=True)
        for folder in ("judgments/gpt56", "judgments/deepseek", "audit"):
            (run_dir / folder).mkdir(parents=True)
            (run_dir / folder / f"{rid}.json").write_text("{}")
        record = {"run_id": rid, "paper_id": "PMC10759803", "query_level": "broad", "benchmark": "v3.1",
                  "query": query, "models": {"writer": "trapi:o3-mini_2025-01-31"}, "status": "ok",
                  "audit": {}, "target_free_asserted": not oracle}
        if oracle:
            record["oracle_diagnostic"] = "hint_lever"
        (run_dir / "runs" / f"{rid}.json").write_text(json.dumps(record))
        self.assertEqual(hashlib.sha256(query.encode()).hexdigest(),
                         M.frozen_queries(M.CASES, M.EXTRA_CASES["v3.1"])[("PMC10759803", "broad")]["sha256"])
        return run_dir

    def test_oracle_runs_pass_only_with_the_flag_and_only_in_oracle_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            good = self.write_run(Path(tmp), "oracle_hint_lever_b_o3mini", oracle=True)
            misplaced = self.write_run(Path(tmp), "writer_only_b_o3mini", oracle=True)
            self.assertFalse(M.check(good, loop=True)["passed"])
            result = M.check(good, loop=True, oracle=True)
            self.assertTrue(result["passed"])
            self.assertTrue(any("oracle diagnostic" in w for w in result["warnings"]))
            self.assertFalse(M.check(misplaced, loop=True, oracle=True)["passed"])


class MeasureTests(unittest.TestCase):
    def test_copying_terms_exclude_the_question(self) -> None:
        g = {"intervention": "Add 5 at.% Al to HfNbTaTiZr and anneal at 1200 °C", "mechanism": "Al2O3 scale forms"}
        t = D.terms(g, "Improve HfNbTaTiZr oxidation at 1200 °C")
        self.assertEqual(t["formulas"], {"Al2O3"})
        self.assertEqual(t["numbers"], {"5at%"})
        self.assertIn("anneal", t["words"])
        self.assertNotIn("oxidation", t["words"])
        share = D.found(t, "An Al2O3 scale formed after adding 5 at.% Al.")
        self.assertEqual(share["formulas"], 1.0)
        self.assertEqual(share["numbers"], 1.0)

    def test_pairwise_scoring_needs_both_orders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.object(D, "DIAG", Path(tmp)):
            folder = Path(tmp) / "pairwise" / "Q64_vs_closed" / "o1"
            folder.mkdir(parents=True)
            outcomes = {"PA__broad__s1": (True, True), "PA__broad__s2": (False, False), "PB__broad__s1": (True, False)}
            for stem, (first, second) in outcomes.items():
                for order, info in (("closed_first", first), ("info_first", second)):
                    (folder / f"{stem}__{order}.json").write_text(json.dumps(
                        {"winner": "B" if (order == "closed_first") == info else "A", "info_won": info,
                         "closed_won": not info}))
            (folder / "PC__broad__s1__closed_first.json").write_text(json.dumps(
                {"winner": "B", "info_won": True, "closed_won": False}))  # one order only: not scored
            res = D.pairwise_results()["Q64_vs_closed"]["o1"]
        self.assertEqual(res["pairs"], 3)
        self.assertEqual(res["info_wins_both_orders"], round(1 / 3, 3))
        self.assertEqual(res["closed_wins_both_orders"], round(1 / 3, 3))
        self.assertEqual(res["net_preference_for_info"]["papers"], 2)  # PA: (+1 - 1) / 2 = 0; PB: 0


if __name__ == "__main__":
    unittest.main()
