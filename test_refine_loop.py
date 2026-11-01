"""Tests for experiment 44 (loop.md 25.1): focused retrieval (focused_search.py) and the refinement loop
(refine_loop.py). No API calls: every model answer is faked."""

from __future__ import annotations

import random
import unittest
from typing import Any
from unittest.mock import patch

import focused_search as FS
import refine_loop as RL
from temporal_hypothesis_benchmark import RetrievalRecord


def rec(pid: str, n: int, text: str, title: str = "T") -> RetrievalRecord:
    return RetrievalRecord(f"{pid}::web::{n:03d}::results", pid, "2020-01-01", "web:Results", text,
                           {"source": "web", "title": title, "dates": {"crossref": "2020-01-01"}})


class FakeHarness:
    def __init__(self, answers: dict[str, Any] | None = None) -> None:
        self.query, self.cutoff, self.level = "How can oxidation of HfNbTaTiZr be limited at 1000 C?", "2024-06-01", "broad"
        self.case = {"paper_id": "PMCX"}
        self.rng = random.Random(1)
        self.seen: dict[str, RetrievalRecord] = {}
        self.notes: dict[str, Any] = {}
        self.models: dict[str, str] = {}
        self.trace: list[dict[str, Any]] = []
        self.answers = answers or {}
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.source = "web"

    def ask(self, role: str, model: str, system: str, payload: dict[str, Any], max_out: int | None = None) -> Any:
        self.calls.append((role, model, payload))
        for prefix, answer in self.answers.items():
            if role.startswith(prefix):
                return answer(payload) if callable(answer) else answer
        return {}


class PlanTests(unittest.TestCase):
    def test_parse_plan_cleans_and_validates(self) -> None:
        plan = FS.parse_plan({"groups": {"material": ['"HfNbTaTiZr" OR x', "refractory high-entropy alloy"],
                                         "Property!": ["oxidation (high temperature)"], "empty": []},
                              "searches": [["material", "property"], ["material"], ["material", "nope"],
                                           ["material", "property"], ["material", "property", "material"]]})
        self.assertEqual(plan["groups"]["material"], ["HfNbTaTiZr x", "refractory high-entropy alloy"])
        self.assertEqual(plan["groups"]["property"], ["oxidation high temperature"])
        self.assertNotIn("empty", plan["groups"])
        self.assertEqual(plan["searches"], [["material", "property"]])

    def test_parse_plan_accepts_search_variants_and_falls_back(self) -> None:
        groups = {"material systems": ["HfMoTaTiZr"], "properties": ["density"], "mechanisms": ["Al substitution"]}
        plan = FS.parse_plan({"groups": groups, "searches": [[["material systems", "properties"], "why"],
                                                             {"groups": ["material systems", "mechanisms"]},
                                                             "properties AND mechanisms"]})
        self.assertEqual(plan["searches"], [["materialsystems", "properties"], ["materialsystems", "mechanisms"],
                                            ["properties", "mechanisms"]])
        plan = FS.parse_plan({"groups": groups, "searches": [["nope"]]})
        self.assertEqual(plan["searches"], [["materialsystems", "properties"], ["materialsystems", "mechanisms"]])
        self.assertTrue(plan["fallback_searches"])

    def test_query_for(self) -> None:
        query = FS.query_for({"a": ["x y", "z"], "b": ["w"]}, ["a", "b"], "2024-06-01")
        self.assertTrue(query.startswith('(TITLE_ABS:"x y" OR TITLE_ABS:"z") AND (TITLE_ABS:"w") AND '))
        self.assertIn("FIRST_PDATE:[1900-01-01 TO 2024-05-31]", query)
        self.assertIn("NOT SRC:PPR", query)

    def test_search_backs_off_to_two_groups(self) -> None:
        calls = []

        def search(query, limit, core=False):
            calls.append(query)
            hits = 0 if query.count("TITLE_ABS") == 3 else 5
            return {"query": query, "hit_count": hits, "fetched": hits, "searched_at": "d",
                    "rows": [{"pmcid": f"P{len(calls)}{i}"} for i in range(hits)]}

        flt = type("F", (), {"cutoff": "2024-06-01"})()
        plan = {"groups": {"a": ["x"], "b": ["y"], "c": ["z"]}, "searches": [["a", "b", "c"]]}
        with patch.object(FS.ws, "search", side_effect=search):
            pmcids, log = FS.run_searches(plan, flt)
        self.assertEqual(len(calls), 2)
        self.assertEqual(log[0]["groups"], ["a", "b"])
        self.assertEqual(len(pmcids), 5)


class GradingTests(unittest.TestCase):
    def test_screen_shuffles_and_defaults_ungraded_to_zero(self) -> None:
        rows = [{"pmcid": f"P{i}", "title": f"t{i}", "abstractText": "a"} for i in range(25)]

        def answer(payload):
            return {"grades": [{"id": item["id"], "grade": 3 if item["title"] == "t0" else 1}
                               for item in payload["papers"] if item["title"] != "t1"]}

        h = FakeHarness({"screener": answer})
        grades = FS.screen(h, rows)
        self.assertEqual(len(h.calls), 2)
        self.assertEqual(grades["P0"]["grade"], 3)
        self.assertEqual(grades["P1"], {"grade": 0, "why": "ungraded"})
        first_batch = [p["title"] for p in h.calls[0][2]["papers"]]
        self.assertNotEqual(first_batch, [f"t{i}" for i in range(20)])  # seeded shuffle, not search order

    def test_pack_orders_by_grade_and_respects_budget(self) -> None:
        records = [rec("P1", 0, "a " * 300), rec("P2", 1, "b " * 300), rec("P3", 2, "c " * 300),
                   rec("P4", 3, "d " * 300)]
        grades = {records[0].record_id: 2, records[1].record_id: 3, records[2].record_id: 1,
                  records[3].record_id: 3}
        packed = FS.pack(records, grades, {"P2": 2, "P4": 3}, budget=1400)
        self.assertEqual([r.paper_id for r in packed], ["P4", "P2"])  # grade 3 first, by paper grade; grade 1 never
        packed = FS.pack(records, grades, {}, budget=10000, exclude={records[3].record_id})
        self.assertEqual([r.paper_id for r in packed], ["P2", "P1"])


def candidate(name: str, ids: list[str] | None = None) -> dict[str, Any]:
    return {"hypothesis": f"{name} hypothesis", "material_initial_state": "m", "intervention": f"{name} lever",
            "conditions": "c", "structural_mediator": "s", "mechanism": f"{name} mechanism",
            "predicted_outcome": "o", "baseline": "b", "boundary": "x", "uncertainty": "u",
            "supporting_evidence_ids": ids or [], "conflicting_evidence_ids": [],
            "falsification_experiment": {"design": "d", "measurements": ["m"], "falsification_rule": "r"}}


def review(score: int, major: bool = False) -> dict[str, Any]:
    return {"scores": {c: score for c in RL.CRITERIA}, "major_issues": ["bad"] if major else [], "minor_issues": [],
            "fixes": [], "evidence_needs": ["need"]}


class LoopTests(unittest.TestCase):
    def test_parse_candidates_filters_unknown_ids(self) -> None:
        raw = {"hypotheses": [candidate("A", ["ok", "bad"]), {"hypothesis": ""}, "x", candidate("B")]}
        out = RL.parse_candidates(raw, {"ok"})
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["fields"]["supporting_evidence_ids"], ["ok"])
        self.assertEqual(out[0]["fields"]["citation_validation"]["removed_unknown_ids"], ["bad"])

    def test_parse_reviews_requires_all_scores(self) -> None:
        raw = {"reviews": [{"id": "a", "scores": {c: 4 for c in RL.CRITERIA}, "major_issues": ["x"]},
                           {"id": "B", "scores": {"soundness": 9}}, {"id": "Z", "scores": {c: 4 for c in RL.CRITERIA}}]}
        out = RL.parse_reviews(raw, ["A", "B"])
        self.assertEqual(list(out), ["A"])
        self.assertEqual(out["A"]["major_issues"], ["x"])

    def test_aggregate_uses_ranks_and_majority_fine(self) -> None:
        reviews = {"o1": {"0": review(2), "1": review(3)},  # harsh critic
                   "4o": {"0": review(5), "1": review(4)},
                   "llama": {"0": review(5, major=True), "1": review(4)}}
        ranked = RL.aggregate(reviews, 2)
        self.assertEqual(ranked[0]["index"], 1)  # fine (two clean critics) beats a better mean rank that is not
        self.assertTrue(ranked[0]["fine"])
        self.assertFalse(ranked[1]["fine"])
        self.assertEqual(RL._ranks({"a": 3.0, "b": 3.0, "c": 1.0}), {"a": 1.5, "b": 1.5, "c": 3.0})

    def run_loop(self, scores: dict[str, int], revise_rounds: bool = True, major: frozenset[str] = frozenset()
                 ) -> tuple[dict, FakeHarness]:
        """scores[name] = the score every critic gives the candidate called name (no major issues); round-1
        candidates are c0..c3, the revisions of round r are r{r}_0..r{r}_3; unknown names score 1."""
        state = {"round": 1}

        def critic(payload):
            return {"reviews": [{"id": item["id"], "scores": {c: scores.get(item["hypothesis"].split()[0], 1)
                                                           for c in RL.CRITERIA},
                                 "major_issues": ["flaw"] if item["hypothesis"].split()[0] in major else [],
                                 "evidence_needs": ["more data"]} for item in payload["candidates"]]}

        def reviser(payload):
            state["round"] += 1
            return {"hypotheses": [{**candidate(f"r{state['round']}_{i}"), "revises": "A", "changes": "x"}
                                   for i in range(RL.K)]}

        h = FakeHarness({"critic": critic, "reviser": reviser, "followup_planner": {
            "groups": {"a": ["oxidation"], "b": ["silicide"]}, "searches": [["a", "b"]], "purpose": "p"}})
        h.pool = lambda representation: [rec("Q1", 0, "oxidation silicide coating " * 20)]
        cands = [{"fields": candidate(f"c{i}"), "revises": "", "changes": ""} for i in range(RL.K)]
        with patch.object(RL.FS, "followup", side_effect=AssertionError("no live search in non-focused arms")):
            final = RL.critique_loop(h, [], cands, focused=False, literature_map=None, revise_rounds=revise_rounds)
        return final, h

    def test_revises_once_even_when_round_one_is_fine(self) -> None:
        final, h = self.run_loop({"c0": 3, "c1": 4, "c2": 2, "c3": 2})  # c1 fine in round 1; revisions all score 1
        self.assertEqual(sum(c[0].startswith("reviser") for c in h.calls), 1)
        self.assertEqual(h.notes["loop"]["stop"], "fine")
        self.assertEqual(h.notes["loop"]["critique_rounds"], 2)
        self.assertEqual(final["hypothesis"], "c1 hypothesis")

    def test_stops_when_a_revision_is_fine(self) -> None:
        final, h = self.run_loop({"c0": 3, "r2_2": 4})
        self.assertEqual(h.notes["loop"]["stop"], "fine")
        self.assertEqual(final["hypothesis"], "r2_2 hypothesis")

    def test_revises_until_max_rounds_and_keeps_parent(self) -> None:
        # Each round a revision is strictly better but keeps a major issue, so it is never fine.
        final, h = self.run_loop({"c0": 2, "r2_1": 3, "r3_2": 4}, major=frozenset({"r3_2"}))
        loop = h.notes["loop"]
        self.assertEqual(loop["critique_rounds"], 3)
        self.assertEqual(loop["stop"], "max_rounds")
        self.assertEqual(len(loop["rounds"][1]["candidates"]), RL.K + 1)  # the previous best stays eligible
        self.assertEqual(loop["rounds"][1]["candidates"][0]["hypothesis"], "c0 hypothesis")
        self.assertEqual(len(h.notes["re_retrieval"]), 2)
        self.assertEqual(h.notes["re_retrieval"][0]["search"]["backend"], "bm25_experiment36_corpus")
        self.assertEqual(final["hypothesis"], "r3_2 hypothesis")

    def test_a_tie_keeps_the_parent(self) -> None:
        final, h = self.run_loop({"c0": 3, "r2_1": 3})
        self.assertEqual(h.notes["loop"]["stop"], "no_improvement")
        self.assertEqual(final["hypothesis"], "c0 hypothesis")

    def test_stops_when_parent_wins_again(self) -> None:
        final, h = self.run_loop({"c0": 3})  # every revision scores 1: the unchanged parent wins round 2
        self.assertEqual(h.notes["loop"]["stop"], "no_improvement")
        self.assertEqual(final["hypothesis"], "c0 hypothesis")

    def test_select_only(self) -> None:
        final, h = self.run_loop({"c1": 3}, revise_rounds=False)
        self.assertEqual(h.notes["loop"]["stop"], "select_only")
        self.assertEqual(final["hypothesis"], "c1 hypothesis")

    def test_budgets(self) -> None:
        self.assertLessEqual(RL.LOOP_START + (RL.MAX_ROUNDS - 1) * RL.REVISION_BUDGET, RL.BUDGET)
        records = [rec(f"P{i}", i, "x " * 700) for i in range(10)]
        fitted = RL.fit_budget(records, 5000)
        self.assertTrue(0 < len(fitted) < 10)
        self.assertEqual(fitted, records[:len(fitted)])

    def test_critics_see_shuffled_neutral_candidates_without_ids(self) -> None:
        seen_orders = []

        def critic(payload):
            seen_orders.append([c["hypothesis"] for c in payload["candidates"]])
            self.assertTrue(all("supporting_evidence_ids" not in c for c in payload["candidates"]))
            self.assertEqual([c["id"] for c in payload["candidates"]], ["A", "B", "C", "D"])
            return {"reviews": []}

        h = FakeHarness({"critic": critic})
        h.seen["S1"] = rec("P9", 1, "cited passage text")
        cands = [{"fields": candidate(f"c{i}", ["S1"] if i == 0 else []), "revises": "", "changes": ""}
                 for i in range(4)]
        reviews = RL.critique(h, cands, 1)
        self.assertEqual(set(reviews), set(RL.CRITICS))
        self.assertEqual(len({tuple(o) for o in seen_orders}) > 1, True)


if __name__ == "__main__":
    unittest.main()
