from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import hypo_loop as H
import query_builder_v4_scimon as V
import v4_scimon_analysis as A


class ComposeTests(unittest.TestCase):
    def test_scimon_template_and_no_context_form(self) -> None:
        rel = {"head": "Cr addition", "head_type": "Material", "tail": "oxidation resistance."}
        self.assertEqual(V.compose(["HEAs oxidise.", "This limits use."], rel),
                         "Consider the following context: HEAs oxidise. This limits use. In that context, which "
                         "material can be used for oxidation resistance, and why?")
        self.assertEqual(V.compose([], rel), "Which material can be used for oxidation resistance, and why?")


class SensorTests(unittest.TestCase):
    TEXT = "We use spark plasma sintering for densification of CoCrFeNi powders. Hardness increases."

    def test_relations_keep_only_verbatim_spans_whose_seed_hides_the_head(self) -> None:
        raw = {"relations": [
            {"head": "spark plasma sintering", "head_type": "Method", "tail": "densification of CoCrFeNi powders"},
            {"head": "spark plasma sintering", "head_type": "Method", "tail": "spark plasma sintering densification"},
            {"head": "ball milling", "head_type": "Method", "tail": "densification"},
            {"head": "CoCrFeNi powders", "head_type": "Task", "tail": "hardness"}]}
        with patch.object(V, "_o3", return_value=raw):
            kept = V.relations(self.TEXT)
        self.assertEqual(kept, [{"head": "spark plasma sintering", "head_type": "Method",
                                 "tail": "densification of CoCrFeNi powders"}])

    def test_classify_defaults_invalid_labels_to_other(self) -> None:
        raw = {"labels": [{"index": 0, "label": "Background"}, {"index": 1, "label": "Intro"},
                          {"index": 7, "label": "Method"}]}
        with patch.object(V, "_o3", return_value=raw):
            self.assertEqual(V.classify(["a", "b", "c"]), ["Background", "Other", "Other"])

    def test_build_drops_self_reference_tries_next_relation_and_flags(self) -> None:
        case = {"paper_id": "PMCX", "publication_date": "2024-06-01", "split": "test2", "hidden_target": {"a": "b"}}
        sentences = ["HEAs are promising.", "Here, we propose a coating.", "We apply the coating to resist oxidation."]
        rels = [{"head": "coating", "head_type": "Material", "tail": "first"},
                {"head": "coating", "head_type": "Material", "tail": "second"}]
        checks = [{"passed": False, "overlap": 0.2, "steers_to_answer": True, "leaks": [1]},
                  {"passed": True, "overlap": 0.0, "steers_to_answer": False, "leaks": []}]
        with tempfile.TemporaryDirectory() as tmp, patch.object(V, "OUT", Path(tmp)), \
                patch.object(V, "CASES_OUT", Path(tmp) / "cases"), \
                patch.object(V, "abstract_sentences", return_value=sentences), \
                patch.object(V, "classify", return_value=["Background", "Background", "Method"]), \
                patch.object(V, "relations", return_value=rels), patch.object(V.v3, "check", side_effect=checks):
            out = V.build_case(case)
        self.assertEqual(out["scimon"]["background_sentences"], ["HEAs are promising."])
        self.assertEqual(out["scimon"]["dropped_self_reference"], ["Here, we propose a coating."])
        self.assertEqual(out["scimon"]["seed"], "second")
        self.assertEqual(out["flags"], [])
        self.assertEqual(out["hidden_target"], {"a": "b"})

    def test_no_relation_fallback_is_flagged_failed_gate_only_when_its_check_fails(self) -> None:
        case = {"paper_id": "PMCY", "publication_date": "2024-06-01", "split": "test", "hidden_target": {"a": "b"}}
        sentences = ["HEAs are promising.", "We measured the hardness."]
        for passed, expected in ((True, ["no_relation"]), (False, ["no_relation", "failed_gate"])):
            check = {"passed": passed, "overlap": 0.0, "steers_to_answer": not passed, "leaks": []}
            with tempfile.TemporaryDirectory() as tmp, patch.object(V, "OUT", Path(tmp)), \
                    patch.object(V, "CASES_OUT", Path(tmp) / "cases"), \
                    patch.object(V, "abstract_sentences", return_value=sentences), \
                    patch.object(V, "classify", return_value=["Background", "Result"]), \
                    patch.object(V, "relations", return_value=[]), patch.object(V.v3, "check", return_value=check):
                out = V.build_case(case)
            self.assertEqual(out["flags"], expected)
            self.assertEqual(out["queries"][V.LEVEL]["passed_gate"], passed)
            self.assertIn("the stated problem", out["queries"][V.LEVEL]["text"])
            self.assertIsNone(out["scimon"]["seed"])

    def test_summary_counts_unflagged_and_gate(self) -> None:
        def built(flags: list[str], passed: bool) -> dict:
            return {"flags": flags, "queries": {V.LEVEL: {"passed_gate": passed, "steers_to_answer": not passed,
                                                          "overlap": 0.1}},
                    "scimon": {"background_sentences": ["x"], "relation_rank": 1, "target_type": "Method"}}
        s = V.summarise([built([], True), built(["no_relation"], True), built(["failed_gate"], False)])
        self.assertEqual((s["cases"], s["unflagged"], s["passed_gate"], s["steers_to_answer"]), (3, 1, 2, 1))
        self.assertEqual(s["flags"], {"no_relation": 1, "failed_gate": 1})


class CommittedCasesTests(unittest.TestCase):
    def test_inputs_are_verbatim_and_targets_unchanged(self) -> None:
        originals = H.cases()
        paths = sorted(V.CASES_OUT.glob("PMC*.json"))
        self.assertEqual(len(paths), 36)
        for path in paths:
            case = json.loads(path.read_text())
            abstract = V._norm(" ".join(V.abstract_sentences(case["paper_id"])))
            for sentence in case["scimon"]["background_sentences"]:
                self.assertIn(V._norm(sentence), abstract)
            if case["scimon"]["seed"]:
                self.assertIn(V._norm(case["scimon"]["seed"]), abstract)
            self.assertEqual(case["hidden_target"], originals[case["paper_id"]]["hidden_target"])
            text = case["queries"][V.LEVEL]["text"]
            self.assertTrue(text.startswith("Consider the following context: ") or text.startswith("Which "))
            self.assertTrue(text.endswith(", and why?"))


class AnalysisHelperTests(unittest.TestCase):
    def test_holm_is_step_down_and_monotone(self) -> None:
        self.assertEqual(A.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])
        self.assertEqual(A.holm([0.5, 0.9]), [1.0, 1.0])

    def test_paired_reports_mean_difference_sign_test_and_ci(self) -> None:
        res = A.paired({"x": 1.0, "y": 2.0, "z": 3.0, "w": 0.5}, {"x": 0.0, "y": 0.0, "z": 0.0, "w": 0.5})
        self.assertEqual((res["papers"], res["up"], res["down"]), (4, 3, 0))
        self.assertAlmostEqual(res["diff"], 1.5)
        self.assertAlmostEqual(res["p"], 0.25)
        self.assertLessEqual(res["ci95"][0], res["diff"])
        self.assertGreaterEqual(res["ci95"][1], res["diff"])
        self.assertEqual(A.paired({"x": 1.0}, {"x": 0.0}, papers={"q"}), {"papers": 0})

    def test_spearman_uses_average_ranks(self) -> None:
        self.assertEqual(A.spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertEqual(A.spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertAlmostEqual(A.spearman([1, 1, 2, 3], [1, 2, 3, 4]), 0.949, places=3)
        self.assertIsNone(A.spearman([1, 1, 1], [1, 2, 3]))

    def test_flag_groups(self) -> None:
        self.assertEqual(A.flag_group({"flags": []}), "clean")
        self.assertEqual(A.flag_group({"flags": ["no_background"]}), "flagged_passed_gate")
        self.assertEqual(A.flag_group({"flags": ["no_relation"]}), "flagged_passed_gate")
        self.assertEqual(A.flag_group({"flags": ["no_background", "failed_gate"]}), "failed_gate")

    def test_style_features_match_the_loop_final_definitions(self) -> None:
        run = {"generation": {"hypothesis": "Al may raise it", "intervention": "add Al", "mechanism": "alumina",
                              "predicted_outcome": "possibly lower mass gain"}}
        feats = A.style_features(run, {"specificity": {"a": True, "b": False}})
        self.assertEqual(feats["length_chars"], float(len("Al may raise it add Al alumina possibly lower mass gain")))
        self.assertEqual(feats["hedges"], 2.0)
        self.assertEqual(feats["specificity"], 0.5)
        self.assertNotEqual(A.style_features(run, None)["specificity"], A.style_features(run, None)["specificity"])


if __name__ == "__main__":
    unittest.main()
