from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import answer_render
import benchmark_test2 as B
import checklist_judge as C
import hypo_loop as H
import loop_methods as L
import must_obey_check as MC
import review_analysis as RA
import review_measurement as M

KEY = {"material_initial_state": "HfNbTaTiZr as cast", "intervention": "add 10 at.% Al", "conditions": "1000 C air",
       "structural_mediator": "Al2O3 scale", "mechanism": "selective oxidation", "predicted_outcome": "lower mass gain",
       "baseline": "Al-free alloy", "boundary": "below 1200 C", "discriminating_measurement": "TGA",
       "actual_result": "mass gain fell by half"}


class RenderTests(unittest.TestCase):
    def test_render_copies_key_fields_into_the_schema(self) -> None:
        g = answer_render.render(KEY)
        self.assertEqual(g["intervention"], "add 10 at.% Al")
        self.assertEqual(g["falsification_experiment"]["measurements"], ["TGA"])
        self.assertIn("selective oxidation", g["hypothesis"])
        self.assertNotIn("mass gain fell by half", json.dumps(g))  # actual_result is not a hypothesis field
        self.assertEqual(answer_render.render({})["falsification_experiment"]["measurements"], [])


class OutputAuditTests(unittest.TestCase):
    def test_flags(self) -> None:
        ok = {"status": "ok", "generation": {"hypothesis": "A method for oxidation resistance is unknown due to lack "
                                                           "of evidence", "intervention": "", "mechanism": ""},
              "models": {"writer": "x", "writer_repair": "x"}, "trace": [{"event": "truncated"}]}
        f = M.run_flags(ok)
        self.assertTrue(f["empty_core"] and f["abstention"] and f["repair"] and f["truncation_retry"])
        self.assertEqual(M.run_flags({"status": "failed"}), {"failed": True})
        good = {"status": "ok", "generation": {"hypothesis": "Adding Al forms an alumina scale that slows oxidation.",
                                               "intervention": "Al", "mechanism": "scale"}, "models": {}, "trace": []}
        self.assertFalse(any(M.run_flags(good).values()))


class ControlsTests(unittest.TestCase):
    def _cases(self) -> dict:
        def case(pid: str, intervention: str, mechanism: str, gap: str) -> dict:
            return {"paper_id": pid, "split": "dev", "gap": {"gap_type": gap},
                    "queries": {"problem_constrained": {"text": f"question {pid}"}},
                    "hidden_target": {**KEY, "intervention": intervention, "mechanism": mechanism}}
        return {"P1": case("P1", "add Al to HfNbTaTiZr", "alumina scale growth", "design"),
                "P2": case("P2", "add Al to HfNbTaTiZr alloy", "alumina scale growth kinetics", "understanding"),
                "P3": case("P3", "laser cladding of CoCrFeNi", "grain refinement", "method"),
                "P4": case("P4", "Si addition", "silica formation", "design")}

    def test_six_controls_per_paper_with_the_right_swaps(self) -> None:
        cases = self._cases()
        items = {i["run_id"]: i for i in M.build_controls(cases)}
        self.assertEqual(len(items), 6 * len(cases))
        self.assertEqual(items["P1__hard_negative"]["source"], "P2")
        self.assertNotEqual(items["P1__random_negative"]["source"], "P2")
        self.assertEqual(items["P1__intervention_swap"]["generation"]["intervention"], "add Al to HfNbTaTiZr alloy")
        self.assertEqual(items["P1__intervention_swap"]["generation"]["mechanism"], "alumina scale growth")
        self.assertEqual(items["P1__mechanism_swap"]["generation"]["mechanism"], "alumina scale growth kinetics")
        self.assertEqual(items["P1__mechanism_swap"]["generation"]["intervention"], "add Al to HfNbTaTiZr")
        self.assertEqual(items["P3__generic"]["generation"]["hypothesis"], M.GENERIC["method"]["hypothesis"])
        self.assertEqual(items["P2__positive"]["query"], "question P2")

    def test_summary_checks(self) -> None:
        def s(i: int, c: int, m: int, o: int) -> dict:
            return {"scores": {"intervention_reconstruction": i, "condition_agreement": c, "mechanism_agreement": m,
                               "outcome_agreement": o}}
        scores = {"gpt56": {}}
        for p in ("P1", "P2"):
            scores["gpt56"].update({f"{p}__positive": s(4, 4, 4, 4), f"{p}__hard_negative": s(1, 1, 1, 1),
                                    f"{p}__random_negative": s(0, 0, 0, 0), f"{p}__intervention_swap": s(1, 4, 4, 4),
                                    f"{p}__mechanism_swap": s(4, 4, 1, 4), f"{p}__generic": s(0, 1, 0, 1)})
        out = M.controls_summary(scores)["gpt56"]
        self.assertEqual(out["auc_positive_vs_negatives"], 1.0)
        self.assertTrue(all(out["checks"].values()))

    def test_auc_kappa_and_flag_rule(self) -> None:
        self.assertEqual(M.auc([2, 3], [1, 2]), 0.875)
        self.assertEqual(M.kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]), 1.0)
        ok = {"overall": "ok", "fields": {"intervention": "supported", "mechanism": "supported"}}
        major = {"overall": "major", "fields": {"intervention": "supported", "mechanism": "supported"}}
        unsupported = {"overall": "minor", "fields": {"intervention": "unsupported", "mechanism": "supported"}}
        self.assertTrue(M.flagged(major, major))
        self.assertTrue(M.flagged(major, unsupported))
        self.assertFalse(M.flagged(major, ok))
        self.assertFalse(M.flagged(ok, unsupported))

    def test_take_respects_per_paper_cap(self) -> None:
        rows = [{"run": {"run_id": f"P1__{i}", "paper_id": "P1"}, "gpt": i} for i in range(3)] + \
               [{"run": {"run_id": "P2__0", "paper_id": "P2"}, "gpt": 5}]
        taken: set[str] = set()
        got = M._take(rows, lambda r: (r["gpt"], r["run"]["run_id"]), 3, 1, taken)
        self.assertEqual([r["run"]["run_id"] for r in got], ["P1__0", "P2__0"])


class ChecklistTests(unittest.TestCase):
    FACTS = [{"id": "f1", "dimension": "intervention", "core": True, "text": "Al is added"},
             {"id": "f2", "dimension": "mechanism", "core": True, "text": "alumina scale forms"},
             {"id": "f3", "dimension": "outcome", "core": False, "text": "mass gain falls"},
             {"id": "f4", "dimension": "conditions", "core": False, "text": "tested at 1000 C"}]

    def test_quote_verification(self) -> None:
        text = "Adding 10 at.% Al forms a continuous alumina scale at 1000 C."
        self.assertEqual(C.verify_quote("continuous alumina scale", text), "exact")
        self.assertEqual(C.verify_quote("alumina continuous scale forms", text), "loose")
        self.assertEqual(C.verify_quote("silica layer grows", text), "none")
        self.assertEqual(C.verify_quote("", text), "none")

    def test_parse_and_score(self) -> None:
        text = "Adding 10 at.% Al forms a continuous alumina scale."
        raw = {"facts": [{"id": "f1", "quote": "Adding 10 at.% Al", "verdict": "yes", "given_in_question": False},
                         {"id": "f2", "quote": "continuous alumina scale", "verdict": "partial",
                          "given_in_question": False},
                         {"id": "f3", "quote": "mass gain halves", "verdict": "yes", "given_in_question": False},
                         {"id": "f4", "quote": "", "verdict": "no", "given_in_question": True}]}
        verdicts, stats = C.parse_verdicts(raw, self.FACTS, text)
        self.assertEqual(verdicts["f3"]["verdict"], "no")  # unverifiable quote downgraded
        self.assertEqual(stats["quote_none"], 1)
        score = C.score_from(self.FACTS, verdicts)
        self.assertEqual(score["dimensions"], {"intervention": 1.0, "mechanism": 0.5, "outcome": 0.0})
        self.assertEqual(score["checklist"], 2.0)  # conditions excluded: given in the question
        self.assertEqual(score["core"], 3.0)

    def test_clean_facts_keeps_valid_dimensions_only(self) -> None:
        raw = {"facts": [{"dimension": "intervention", "text": "Al is added at 10 at.%"},
                         {"dimension": "material", "text": "HfNbTaTiZr alloy is used"},
                         {"dimension": "outcome", "text": "short"}]}
        self.assertEqual([f["dimension"] for f in C.clean_facts(raw)], ["intervention"])


class EligibilityTests(unittest.TestCase):
    def test_2024_cutoff_models_only_after_cutoff_plus_margin(self) -> None:
        self.assertEqual(H.METHOD_MODELS["writer_only_b_o4mini"], ("o4mini",))
        self.assertTrue(H.eligible("writer_only_b_o4mini", {"publication_date": "2024-07-03"}))
        self.assertFalse(H.eligible("writer_only_b_o4mini", {"publication_date": "2024-07-02"}))
        self.assertFalse(H.eligible("writer_only_b_41", {"publication_date": "2024-07-02"}))
        self.assertTrue(H.eligible("writer_only_b_4o", {"publication_date": "2024-01-02"}))
        self.assertTrue(H.eligible("writer_only_b_o3mini", {"publication_date": "2024-01-02"}))

    def test_models_that_failed_the_probe_are_not_registered(self) -> None:
        for name in ("writer_only_b_o3", "writer_only_b_gpt5"):
            self.assertNotIn(name, H.METHODS)
        for deployment in ("o3_2025-04-16", "gpt-5_2025-08-07"):
            self.assertNotIn(deployment, MC.MODEL_CUTOFFS)
            self.assertNotIn(deployment, {s["deployment"] for s in H.MODELS.values()})

    def test_integrity_gate_fails_strict_margin_models_inside_the_margin(self) -> None:
        self.assertIn("o4-mini_2025-04-16", MC.STRICT_MARGIN)
        with tempfile.TemporaryDirectory() as tmp:
            cases = Path(tmp) / "cases"
            cases.mkdir()
            (cases / "PMCX.json").write_text(json.dumps({"paper_id": "PMCX", "publication_date": "2024-06-20",
                                                         "split": "dev", "queries": {"broad": {"text": "q"}}}))
            runs = Path(tmp) / "run" / "runs"
            runs.mkdir(parents=True)
            (runs / "PMCX__broad__m__s1.json").write_text(json.dumps({
                "run_id": "PMCX__broad__m__s1", "paper_id": "PMCX", "query_level": "broad", "query": "q",
                "status": "ok", "models": {"writer": "trapi:o4-mini_2025-04-16"}, "target_free_asserted": True}))
            with patch.dict(MC.BENCHMARKS, {"v3.1": cases}, clear=False), patch.dict(MC.EXTRA_CASES, {"v3.1": ()}):
                result = MC.check(Path(tmp) / "run", require_cross=False, bench="v3.1")
        self.assertFalse(result["passed"])
        self.assertTrue(any("more than 31 days" in f for f in result["failures"]))


class FewShotAndRouterTests(unittest.TestCase):
    def test_examples_are_earlier_papers_and_never_the_case(self) -> None:
        cases = sorted(H.cases().values(), key=lambda c: c["publication_date"])
        late = cases[-1]
        for mode in ("similar", "diverse"):
            picks = L.pick_exemplars(late["queries"]["broad"]["text"], late, mode)
            self.assertEqual(len(picks), 3)
            self.assertTrue(all(e["date"] < late["publication_date"] and e["paper_id"] != late["paper_id"]
                                for e in picks))
            self.assertNotIn("actual_result", json.dumps(picks[0]["answer"]))
        self.assertEqual(L.pick_exemplars("q", cases[0], "similar"), [])
        diverse = L.pick_exemplars(late["queries"]["broad"]["text"], late, "diverse")
        self.assertGreaterEqual(len({e["gap_type"] for e in diverse}), 2)

    def test_router_falls_back_to_design_on_a_bad_type(self) -> None:
        class FakeHarness:
            query, notes = "How can the oxidation resistance be improved?", {}

            def ask(self, *_a, **_k):
                return {"question_type": "nonsense"}
        with patch.object(L, "write", return_value={"ok": True}) as write:
            h = FakeHarness()
            L.m_router_b(h)
        self.assertEqual(h.notes["route"], "design")
        self.assertEqual(write.call_args[0][1]["guidance"], L.ROUTE_GUIDE["design"])


class Test4ConfigTests(unittest.TestCase):
    def test_configure_sets_size_and_window(self) -> None:
        try:
            B.configure("test4")
            self.assertEqual((B.N_CASES, B.SPLIT, B.EXTEND, B.WINDOW[0]), (24, "test4", False, "2024-11-01"))
            self.assertEqual(B.EXCLUDE_SETS, ("test2", "test3"))
            B.configure("test3")
            self.assertEqual(B.N_CASES, 12)
        finally:
            B.configure("test2")


class AnalysisTests(unittest.TestCase):
    def test_per_paper_means_samples_then_levels(self) -> None:
        scores = {"P__broad__m__s1": {"gpt": 1.0}, "P__broad__m__s2": {"gpt": 3.0}, "P__expert_context__m__s1": {"gpt": 0.0},
                  "Q__broad__m__s1": {"deep": 2.0}}
        self.assertEqual(RA.per_paper(scores, "gpt"), {"P": 1.0})

    def test_finalist_rule(self) -> None:
        item = {"gpt": {"papers": 10, "diff": 0.2, "ci95": [0.05, 0.3]}, "deep": {"papers": 10, "diff": 0.1},
                "checklist_gpt": {"papers": 10, "diff": -0.1}}
        self.assertTrue(all(RA.finalist_rule(item, "writer_only_b_41", False).values()))
        self.assertFalse(all(RA.finalist_rule(item, "writer_only_b_41", True).values()))
        item["deep"]["diff"] = -0.1
        self.assertFalse(all(RA.finalist_rule(item, "writer_only_b_4o", False).values()))


if __name__ == "__main__":
    unittest.main()
