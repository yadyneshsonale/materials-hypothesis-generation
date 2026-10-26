from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import citegraph as cg
import suite_extra_eval as S
import v4_all_analysis as V

ROOT = Path(__file__).resolve().parent


def _levels(env_value: str | None) -> list[str]:
    env = {k: v for k, v in os.environ.items() if k != "MATHG_LEVELS"}
    if env_value is not None:
        env["MATHG_LEVELS"] = env_value
    code = "import json, temporal_hypothesis_benchmark as t; print(json.dumps(list(t.QUERY_LEVELS)))"
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


class QueryLevelTests(unittest.TestCase):
    def test_default_levels_unchanged_and_env_override(self) -> None:
        self.assertEqual(_levels(None), ["broad", "problem_constrained", "expert_context"])
        self.assertEqual(_levels("scimon"), ["scimon"])


class GraphQueryTests(unittest.TestCase):
    def test_graph_query_follows_the_configured_level(self) -> None:
        case = {"queries": {"problem_constrained": {"text": "v3.1 question"}, "scimon": {"text": "v4 input"}}}
        self.assertEqual(cg.graph_query(case), "v3.1 question")
        with patch.object(cg, "GRAPH_LEVEL", "scimon"):
            self.assertEqual(cg.graph_query(case), "v4 input")

    def test_marker_label_accepts_labels_and_copied_marker_text(self) -> None:
        info = {"labels": {"R1": "rid1", "R2": "rid2"},
                "markers": {"R1": "Boosting Hot Electrons in Hetero-superstructures (2017)",
                            "R2": "Biaxially strained PtPb/Pt core/shell nanoplate (2016)"}}
        self.assertEqual(cg.marker_label("R2", info), "R2")
        self.assertEqual(cg.marker_label("[R1]", info), "R1")
        self.assertEqual(cg.marker_label("Boosting Hot Electrons in Hetero-superstructures (2017)", info), "R1")
        self.assertEqual(cg.marker_label("biaxially strained PtPb/Pt core/shell nanoplate (2016)", info), "R2")
        self.assertIsNone(cg.marker_label("An unrelated title (2020)", info))
        self.assertIsNone(cg.marker_label("", info))
        same = {"labels": {"R1": "a", "R2": "b"}, "markers": {"R1": "Same title (2019)", "R2": "Same title (2019)"}}
        self.assertIsNone(cg.marker_label("Same title (2019)", same))


def _run(paper: str, setting: str, text: str = "Al raises oxidation resistance") -> dict:
    return {"run_id": f"{paper}__scimon__{setting}", "paper_id": paper, "query_level": "scimon", "setting": setting,
            "status": "ok", "query": "Which method can be used for oxidation resistance, and why?",
            "generation": {"hypothesis": text, "intervention": "add Al", "supporting_evidence_ids": ["R1"]},
            "cited_evidence": [{"record_id": "R1", "paper_id": "PMC1", "publication_date": "2019-01-01", "text": "t"}]}


class SuiteExtraEvalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for sub, setting in (("eval_v3", "closed_book"), ("eval_v4_matkg", "tool_agent_kg"),
                             ("eval_critique/baseline_resample", "tool_agent")):
            (self.root / sub / "runs").mkdir(parents=True)
            run = _run("PMCX", setting)
            (self.root / sub / "runs" / f"{run['run_id']}.json").write_text(json.dumps(run))
        copied = (self.root / "eval_v3" / "runs" / "PMCX__scimon__closed_book.json").read_bytes()
        (self.root / "eval_v4_matkg" / "runs" / "PMCX__scimon__closed_book.json").write_bytes(copied)
        failed = {**_run("PMCX", "tool_agent"), "status": "failed"}
        (self.root / "eval_v3" / "runs" / "PMCX__scimon__tool_agent.json").write_text(json.dumps(failed))
        rev_dir = self.root / "eval_critique" / "revisions" / "critique"
        rev_dir.mkdir(parents=True)
        rev = {"run_id": "PMCX__scimon__tool_agent", "paper_id": "PMCX", "status": "ok", "query": "q",
               "revised_generation": {"hypothesis": "revised", "supporting_evidence_ids": []}, "cited_evidence": []}
        (rev_dir / "PMCX__scimon__tool_agent.json").write_text(json.dumps(rev))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_units_cover_runs_copies_and_revisions_and_skip_failed(self) -> None:
        units = {u["id"]: u for u in S.units(self.root)}
        self.assertEqual(sorted(units), [
            "eval_critique/baseline_resample/PMCX__scimon__tool_agent", "eval_critique/critique/PMCX__scimon__tool_agent",
            "eval_v3/PMCX__scimon__closed_book", "eval_v4_matkg/PMCX__scimon__closed_book",
            "eval_v4_matkg/PMCX__scimon__tool_agent_kg"])
        self.assertIsNotNone(units["eval_v4_matkg/PMCX__scimon__closed_book"]["copy_of"])
        self.assertIsNone(units["eval_v4_matkg/PMCX__scimon__tool_agent_kg"]["copy_of"])
        rev = units["eval_critique/critique/PMCX__scimon__tool_agent"]
        self.assertEqual(rev["run"]["generation"]["hypothesis"], "revised")
        self.assertTrue(str(rev["deep"]).endswith("eval_critique/judgments/deepseek_critique/PMCX__scimon__tool_agent.json"))

    def test_payloads_are_blinded_and_target_free(self) -> None:
        run = _run("PMCX", "closed_book")
        judge = S.judge_payload(run, {"hidden_target": {"intervention": "secret"}})
        self.assertEqual(judge["generated_hypothesis"]["supporting_evidence_ids"], ["E1"])
        self.assertEqual(judge["cited_evidence"][0]["evidence_id"], "E1")
        audit = S.audit_payload(run)
        self.assertNotIn("hidden_target", json.dumps(audit))
        self.assertEqual(set(audit), {"query", "hypothesis", "cited_evidence"})

    def test_stage_scores_fresh_units_and_copies_outputs_for_identical_runs(self) -> None:
        score = {"scores": {k: 1 for k in ("problem_alignment", "intervention_reconstruction", "condition_agreement",
                                           "mechanism_agreement", "outcome_agreement", "baseline_quality",
                                           "boundary_quality", "experiment_discriminability", "evidence_validity",
                                           "novelty")}, "classification": "unsupported"}
        cases = [{"paper_id": "PMCX", "hidden_target": {"intervention": "secret"}}]
        with patch.object(S, "load_cases", return_value=cases), \
                patch.object(S.lc, "trapi_chat_json", return_value=score) as call:
            counts = S.run_stage("cross_judge", 2, self.root)
        self.assertEqual((counts["jobs"], counts["done"], counts["copied"], counts["failed"]), (5, 4, 1, 0))
        self.assertEqual(call.call_count, 4)
        copied = self.root / "eval_v4_matkg" / "judgments" / "deepseek" / "PMCX__scimon__closed_book.json"
        source = self.root / "eval_v3" / "judgments" / "deepseek" / "PMCX__scimon__closed_book.json"
        self.assertEqual(copied.read_bytes(), source.read_bytes())
        with patch.object(S, "load_cases", return_value=cases), patch.object(S.lc, "trapi_chat_json") as again:
            self.assertEqual(S.run_stage("cross_judge", 2, self.root)["jobs"], 0)
            again.assert_not_called()


class AnalysisTests(unittest.TestCase):
    def test_significance_needs_holm_below_005(self) -> None:
        self.assertEqual(V.significant({"papers": 5, "diff": 0.3, "holm_p": 0.01}), 1)
        self.assertEqual(V.significant({"papers": 5, "diff": -0.3, "holm_p": 0.04}), -1)
        self.assertEqual(V.significant({"papers": 5, "diff": 0.3, "holm_p": 0.2}), 0)
        self.assertEqual(V.significant({"papers": 0}), 0)

    def test_compare_all_skips_base_and_missing_and_applies_holm(self) -> None:
        scores = {"base": {p: 0.0 for p in "abcdefgh"}, "up": {p: 1.0 for p in "abcdefgh"},
                  "flat": {p: 0.0 for p in "abcdefgh"}}
        items = V.compare_all(scores, ["base", "up", "flat", "absent"], "base")
        self.assertEqual([i["config"] for i in items], ["up", "flat"])
        self.assertEqual((items[0]["up"], items[0]["p"], items[0]["holm_p"]), (8, 0.0078, 0.0156))
        subset = V.compare_all(scores, ["up"], "base", {"a", "b"})
        self.assertEqual(subset[0]["papers"], 2)

    def test_per_paper_arm_averages_samples_then_levels(self) -> None:
        scores = {("arm", "P1", "broad"): [1.0, 3.0], ("arm", "P1", "expert_context"): [4.0], ("arm", "P2", "scimon"): [1.0]}
        self.assertEqual(V.per_paper_arm(scores), {"arm": {"P1": 3.0, "P2": 1.0}})

    def test_suite_extra_deep_reads_the_helper_layout(self) -> None:
        scores = {"scores": {d: 2 for d in V.A.DIMS}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for sub, setting in (("eval_v3", "tool_agent"), ("eval_v4_matkg", "closed_book"), ("eval_v4_matkg", "tool_agent_kg")):
                run = _run("PMCX", setting)
                for folder in ("runs", "judgments/deepseek"):
                    (root / sub / folder).mkdir(parents=True, exist_ok=True)
                (root / sub / "runs" / f"{run['run_id']}.json").write_text(json.dumps(run))
                (root / sub / "judgments" / "deepseek" / f"{run['run_id']}.json").write_text(json.dumps(scores))
            for folder in ("eval_critique/judgments/deepseek_self_revise", "eval_critique/baseline_resample/judgments/deepseek"):
                (root / folder).mkdir(parents=True)
                (root / folder / "PMCX__scimon__tool_agent.json").write_text(json.dumps(scores))
            got = V.suite_extra_deep(root)
        self.assertEqual(sorted(k[0] for k in got), ["exp11_critique:self_revise", "exp11_critique:tool_agent_resample",
                                                     "exp7_eval_v3:tool_agent", "exp9_matkg:tool_agent_kg"])
        self.assertEqual(got[("exp9_matkg:tool_agent_kg", "PMCX", "scimon")], [2.0])

    def test_harness_configurations_exclude_only_the_replicates(self) -> None:
        configs = V.harness_configs()
        self.assertNotIn("writer_only_b_o3mini_r3", configs)
        self.assertNotIn("trend_ground_b_o3mini_r2", configs)
        self.assertEqual(len(configs), 52)
        self.assertTrue({"closed_book", "writer_only_b_o3mini", "papers_n1_b_o3mini"} <= set(configs))

    def test_style_all_counts_audited_runs_and_correlates_features(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            v4, v31 = Path(tmp) / "v4", Path(tmp) / "v31"
            scores = [0, 1, 2, 3]
            for i, s in enumerate(scores):
                run = {"run_id": f"PMC{i}__scimon__m__s1", "status": "ok", "query_level": "scimon",
                       "generation": {"hypothesis": "x" * (10 * (i + 1)), "predicted_outcome": "may" if i == 0 else ""}}
                for sub in ("runs", "judgments/gpt56", "audit"):
                    (v4 / "m" / sub).mkdir(parents=True, exist_ok=True)
                (v4 / "m" / "runs" / f"{run['run_id']}.json").write_text(json.dumps(run))
                (v4 / "m" / "judgments" / "gpt56" / f"{run['run_id']}.json").write_text(
                    json.dumps({"scores": {d: s for d in V.A.DIMS}}))
                if i < 3:
                    (v4 / "m" / "audit" / f"{run['run_id']}.json").write_text(
                        json.dumps({"specificity": {"a": i > 0, "b": i > 1}}))
            (v31 / "m" / "runs").mkdir(parents=True)
            with patch.object(V.A, "V4_ROOT", v4), patch.object(V.A, "V31_ROOT", v31):
                out = V.style_all(["m"])
        block = out["per_configuration"]["m"]["v4"]
        self.assertEqual((block["runs"], block["audited"], out["audited_v4_runs"]), (4, 3, 3))
        self.assertEqual(block["rho_length_chars"], 1.0)
        self.assertEqual(block["hedges"], 0.25)
        self.assertEqual(out["per_configuration"]["m"]["v31"]["runs"], 0)


if __name__ == "__main__":
    unittest.main()
