"""Tests for experiment 46 (loop.md 27.1): the research-quality instrument (quality_eval.py), run-root discovery in
rq_judge.py and the quality mode of must_obey_check.py. No API calls: every model answer is faked."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import must_obey_check as MC
import quality_eval as Q
import rq_judge as RQ


def run(paper: str, level: str, n_cited: int, sample: int = 1, method: str = "m") -> dict:
    cited = [f"{paper}X{k}::web::{k:03d}::results" for k in range(n_cited)]
    return {"run_id": f"{paper}__{level}__{method}__s{sample}", "paper_id": paper, "query_level": level,
            "sample": sample, "method": method, "query": f"question on {paper}", "status": "ok",
            "generation": {"hypothesis": f"h {paper}", "intervention": "add Al", "supporting_evidence_ids": cited,
                           "conflicting_evidence_ids": [], "citation_validation": {"status": "valid"}},
            "cited_evidence": [{"record_id": c, "paper_id": f"{paper}X{k}", "publication_date": "2020-01-01",
                                "kind": "web:Results", "text": f"passage {k} of {paper}"}
                               for k, c in enumerate(cited)]}


class GroundingJudgeTests(unittest.TestCase):
    def test_validate(self) -> None:
        ok = {"premises": ["a", "b"], "grounding_reason": "r", "grounding": 4}
        self.assertEqual(Q.ground_validate(ok)["grounding"], 4)
        self.assertEqual(Q.ground_validate({**ok, "grounding": "3"})["grounding"], 3)
        for bad in ({**ok, "grounding": 0}, {**ok, "grounding": 6}, {**ok, "grounding": 3.5}, {"premises": []}, []):
            self.assertIsNone(Q.ground_validate(bad))

    def test_payload_shows_hypothesis_and_passages_but_never_the_key(self) -> None:
        view = Q.blinded(run("P1", "broad", 2))
        data = json.loads(Q.ground_payload(view["query"], view["generation"], view["evidence"]))
        self.assertEqual(data["hypothesis"]["supporting_evidence_ids"], ["E1", "E2"])
        self.assertEqual([e["evidence_id"] for e in data["cited_evidence"]], ["E1", "E2"])
        self.assertNotIn("citation_validation", data["hypothesis"])
        with self.assertRaises(Q.H.TargetLeak):
            Q.ground_payload("q", {"hypothesis": "hidden_target"}, [])

    def test_judge_retries_invalid_output(self) -> None:
        replies = [{"grounding": 9}, {"grounding": 2, "grounding_reason": "thin", "premises": ["x"]}]
        with patch.object(Q, "ground_call", side_effect=lambda j, u: replies.pop(0)):
            out = Q.ground_judge("deepseek", Q.blinded(run("P1", "broad", 1)))
        self.assertEqual((out["grounding"], out["attempts"]), (2, 2))
        with patch.object(Q, "ground_call", return_value={"grounding": 0}), self.assertRaises(Q.lc.LLMError):
            Q.ground_judge("deepseek", Q.blinded(run("P1", "broad", 1)))


class ControlTests(unittest.TestCase):
    def test_swap_takes_another_papers_passages_at_the_same_level(self) -> None:
        runs = [run("P1", "broad", 2), run("P2", "broad", 1), run("P3", "broad", 3), run("P4", "expert_context", 2),
                run("P5", "expert_context", 0)]
        swaps = {i: d for k, m, i, d in Q.swap_controls(runs)}
        p1 = swaps["P1__broad__m__s1"]
        self.assertEqual([e["paper_id"] for e in p1["evidence"]], ["P3X0", "P3X1"])  # P2 cites too few
        self.assertEqual([e["evidence_id"] for e in p1["evidence"]], ["E1", "E2"])
        self.assertEqual(p1["generation"]["supporting_evidence_ids"], ["E1", "E2"])
        self.assertEqual([e["paper_id"] for e in swaps["P2__broad__m__s1"]["evidence"]], ["P3X0"])
        self.assertNotIn("P3__broad__m__s1", swaps)  # no other paper at its level cites three passages
        self.assertNotIn("P4__expert_context__m__s1", swaps)  # its only neighbour cites nothing
        self.assertNotIn("P5__expert_context__m__s1", swaps)

    def test_removal_drops_every_citation(self) -> None:
        removed = Q.removal_controls([run("P1", "broad", 2), run("P2", "broad", 0)])
        self.assertEqual(len(removed), 1)
        kind, _, item, data = removed[0]
        self.assertEqual((kind, item, data["evidence"]), ("g_removed", "P1__broad__m__s1", []))
        self.assertEqual(data["generation"]["supporting_evidence_ids"], [])


class PairwiseTests(unittest.TestCase):
    def test_a_win_needs_both_orders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.object(Q, "PAIR_DIR", Path(tmp)):
            outcomes = {("P1", "broad", 1): (True, True), ("P1", "expert_context", 1): (True, False),
                        ("P2", "broad", 1): (False, False)}
            for key, (first, second) in outcomes.items():
                for order, new_won in (("baseline_first", first), ("new_first", second)):
                    path = Q.pair_path("new", "base", "deepseek", key, order)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps({"new_won": new_won, "baseline_won": not new_won}))
            got = Q.pair_outcomes("new", "base", "deepseek")
            self.assertEqual(got, {("P1", "broad", 1): 1.0, ("P1", "expert_context", 1): 0.0,
                                   ("P2", "broad", 1): -1.0})
            self.assertEqual(Q.per_paper(got), {"P1": 0.5, "P2": -1.0})
            result = Q.pair_result("new", "base", "deepseek")
            self.assertEqual((result["pairs"], result["new_wins"], result["base_wins"]), (3, 0.333, 0.333))


class ScoreTests(unittest.TestCase):
    def test_sp_combines_the_four_scales(self) -> None:
        rq = {("P1", "broad", 1): {"scores": {"plausibility": 4, "testability": 4, "usefulness": 5}, "rq": 3.333},
              ("P1", "broad", 2): {"scores": {"plausibility": 3, "testability": 3, "usefulness": 3}, "rq": 2.0}}
        with patch.object(Q, "rq_values", return_value=rq), \
                patch.object(Q, "ground_values", return_value={("P1", "broad", 1): 3}):
            self.assertEqual(Q.sp_values("m"), {("P1", "broad", 1): 3.0})
            self.assertEqual(Q.sp_values("m", with_grounding=False),
                             {("P1", "broad", 1): 3.333, ("P1", "broad", 2): 2.0})

    def test_incumbent_rule(self) -> None:
        def r(lower: float, sp_upper: float, grounding: float, gpt: float | None = None) -> dict:
            pairwise = {"deepseek": {"papers": 45, "diff": lower + 0.1, "ci95": [lower, lower + 0.2]}}
            if gpt is not None:
                pairwise["gpt56"] = {"papers": 45, "diff": gpt, "ci95": [gpt - 0.1, gpt + 0.1]}
            return {"pairwise": pairwise, "sp_vs_writer": {"papers": 45, "ci95": [sp_upper - 0.2, sp_upper]},
                    "grounding": grounding}
        rows = {"a": r(0.10, 0.1, 3.0), "b": r(0.20, -0.01, 3.0), "c": r(0.15, 0.1, 1.0), "d": r(0.30, 0.1, 3.0, -0.1),
                "e": r(-0.1, 0.2, 3.0), Q.REFERENCE: r(0.5, 0.2, 3.0)}
        result = Q.incumbent(rows, writer_grounding=1.5)
        self.assertEqual(result["incumbent"], "a")  # b: SP below the writer; c: less grounded; d: GPT-5.6 disagrees
        self.assertEqual(result["eligible"], ["a"])
        self.assertEqual(Q.incumbent({"e": rows["e"]}, 1.5)["incumbent"], Q.WRITER)


class DiscoveryTests(unittest.TestCase):
    def test_roots_are_found_and_must_be_unique(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for root, method in (("loop", "a"), ("loop_web", "b"), ("loop_v4_scimon", "a")):
                (base / root / method / "runs").mkdir(parents=True)
            self.assertEqual(RQ.discovered_roots(base), {"a": "loop", "b": "loop_web"})
            (base / "loop_pcd" / "a" / "runs").mkdir(parents=True)
            RQ._discover.cache_clear()
            with self.assertRaises(RuntimeError):
                RQ.discovered_roots(base)
        RQ._discover.cache_clear()


class GateTests(unittest.TestCase):
    def test_quality_judged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rq_dir, ground_dir = Path(tmp) / "rq", Path(tmp) / "ground"
            for kind in MC.RQ_CALLS[:2]:
                (rq_dir / kind / "m" / "deepseek").mkdir(parents=True)
                (rq_dir / kind / "m" / "deepseek" / "r1.json").write_text("{}")
            self.assertEqual(MC.quality_judged("m", "r1", rq_dir, ground_dir), {"rq3": False, "grounding": False})
            (rq_dir / "runs_rep3" / "m" / "deepseek").mkdir(parents=True)
            (rq_dir / "runs_rep3" / "m" / "deepseek" / "r1.json").write_text("{}")
            (ground_dir / "runs" / "m" / "deepseek").mkdir(parents=True)
            (ground_dir / "runs" / "m" / "deepseek" / "r1.json").write_text("{}")
            self.assertEqual(MC.quality_judged("m", "r1", rq_dir, ground_dir), {"rq3": True, "grounding": True})


if __name__ == "__main__":
    unittest.main()
