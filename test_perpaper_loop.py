"""Tests for experiment 49 (loop.md 28.1): the per-paper generate -> critique -> narrow method (perpaper_loop.py)
and the teaching-text corpus rules (materials_texts.py). No API calls."""

from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import patch

import materials_texts as MT
import perpaper_loop as P
from temporal_hypothesis_benchmark import RetrievalRecord

PAPER = {"pmcid": "PMC1", "title": "Paper one", "grade": 3}
TEXT = [RetrievalRecord("PMC1::web::000::abstract", "PMC1", "2020-01-01", "web:Abstract", "abstract text",
                        {"source": "web", "title": "Paper one"})]


def hyp(intervention: str, mediator: str = "precipitates") -> dict[str, Any]:
    return {"hypothesis": f"h {intervention}", "intervention": intervention, "structural_mediator": mediator,
            "supporting_evidence_ids": ["PMC1::web::000::abstract"], "conflicting_evidence_ids": [],
            "builds_on": "b", "what_is_new": "n"}


def review(sound: bool = True, testable: bool = True, beyond: bool = True) -> dict[str, Any]:
    return {"sound": {"pass": sound, "reason": "r"}, "testable": {"pass": testable, "reason": "r"},
            "beyond_paper": {"pass": beyond, "reason": "r"}, "fix": "f"}


class FakeHarness:
    """Answers generator calls with three hypotheses and critic calls from a script of verdict lists."""

    def __init__(self, verdicts: list[list[dict[str, Any]]]) -> None:
        self.query, self.cutoff, self.level, self.sample = "the research question", "2024-06-01", "broad", 1
        self.case = {"paper_id": "PMCX"}
        self.seen: dict[str, RetrievalRecord] = {}
        self.notes: dict[str, Any] = {}
        self.models: dict[str, str] = {}
        self.trace: list[dict[str, Any]] = []
        self.verdicts = list(verdicts)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def ask(self, role: str, model: str, system: str, payload: dict[str, Any], max_out: int | None = None) -> Any:
        self.calls.append((role, payload))
        if role.startswith("generator"):
            n = len(self.calls)
            return {"hypotheses": [hyp(f"change {n}-{i}") for i in range(P.K)]}
        if role == "critic":
            return {"reviews": [{"id": f"H{i + 1}", **v} for i, v in enumerate(self.verdicts.pop(0))]}
        raise AssertionError(role)


def run_paper(h: FakeHarness, max_rounds: int) -> dict[str, Any]:
    with patch.object(P, "paper_text", lambda paper: TEXT), patch.object(P, "text_records", lambda q, p, c: []), \
            patch.object(P, "kg_records", lambda h_, p: []):
        return P.per_paper(h, PAPER, max_rounds)


class PerPaperTests(unittest.TestCase):
    def test_acceptance_needs_all_three_criteria(self) -> None:
        raw = {"reviews": [{"id": "H1", **review()}, {"id": "H2", **review(beyond=False)},
                           {"id": "H3", "sound": {"pass": "true"}}]}
        got = P.parse_reviews(raw, 3)
        self.assertEqual([r["accepted"] for r in got], [True, False, False])  # "true" as a string is not a pass

    def test_loop_stops_at_first_accepted_round_and_critic_never_sees_question(self) -> None:
        h = FakeHarness([[review(beyond=False)] * 3, [review(), review(sound=False), review()]])
        log = run_paper(h, max_rounds=20)
        self.assertEqual(log["n_rounds"], 2)
        self.assertEqual([c[0] for c in h.calls], ["generator", "critic", "generator_revise", "critic"])
        self.assertEqual(len(log["accepted"]), 2)
        self.assertEqual({a["round"] for a in log["accepted"]}, {2})
        revise = h.calls[2][1]
        self.assertIn("critique", revise)
        self.assertEqual(len(revise["previous_hypotheses"]), P.K)
        for role, payload in h.calls:
            if role == "critic":
                self.assertNotIn("the research question", str(payload))
                self.assertNotIn("research_question", payload)

    def test_full_log_keeps_every_hypothesis_and_review(self) -> None:
        h = FakeHarness([[review(beyond=False)] * 3, [review(), review(sound=False), review()]])
        h.full_log = True
        log = run_paper(h, max_rounds=20)
        self.assertEqual([len(r["hypotheses"]) for r in log["rounds"]], [P.K, P.K])
        self.assertEqual([[rv["accepted"] for rv in r["reviews"]] for r in log["rounds"]],
                         [[False] * 3, [True, False, True]])
        self.assertIn("background_items", log)
        plain = run_paper(FakeHarness([[review()] * 3]), max_rounds=20)
        self.assertNotIn("hypotheses", plain["rounds"][0])

    def test_paper_is_dropped_after_max_rounds(self) -> None:
        h = FakeHarness([[review(testable=False)] * 3] * 4)
        log = run_paper(h, max_rounds=4)
        self.assertEqual(log["accepted"], [])
        self.assertEqual(log["n_rounds"], 4)
        self.assertEqual(sum(c[0] == "critic" for c in h.calls), 4)
        self.assertEqual(sum(c[0].startswith("generator") for c in h.calls), 4)  # no revision after the last round

    def test_dedupe_merges_same_intervention_and_mediator(self) -> None:
        pool = [{"fields": hyp("aging at 600 C")}, {"fields": hyp("aging at 600 C", "precipitates")},
                {"fields": hyp("add 2 at.% Zr", "grain boundaries")}]
        self.assertEqual(len(P.dedupe(pool)), 2)

    def test_narrow_ranks_by_tournament_wins(self) -> None:
        pool = [{"fields": hyp(f"x{i}"), "strength": s} for i, s in enumerate([1, 5, 3, 2, 4, 0, 6, 7])]
        with patch.object(P, "match", lambda h, a, b: 1.0 if a["strength"] > b["strength"] else 0.0):
            ranked, info = P.narrow(None, pool)
        self.assertEqual(info["format"], "swiss+round_robin")
        self.assertEqual([r["strength"] for r in ranked[:3]], [7, 6, 5])
        with patch.object(P, "match", lambda h, a, b: 1.0 if a["strength"] > b["strength"] else 0.0):
            ranked, info = P.narrow(None, pool[:4])
        self.assertEqual(info["format"], "round_robin")
        self.assertEqual([r["strength"] for r in ranked], [5, 3, 2, 1])

    def test_select_papers_one_per_first_author_by_grade(self) -> None:
        manifest = {"models": {}, "papers": [
            {"pmcid": "A", "grade": 2, "first_author": "lee"}, {"pmcid": "B", "grade": 3, "first_author": "kim"},
            {"pmcid": "C", "grade": 3, "first_author": "kim"}, {"pmcid": "D", "grade": 3, "first_author": "wu"}]}
        h = FakeHarness([])
        with patch.object(P.FS, "build", lambda c, l: manifest):
            got = [p["pmcid"] for p in P.select_papers(h, 3)]
        self.assertEqual(got, ["B", "D", "A"])

    def test_teaching_texts_drop_hea_passages(self) -> None:
        counts = {"dropped_hea": 0}
        long = "x " * 150
        out = MT.passages("wikipedia", "d", "t", "u", "2023-12-31",
                          [("Creep", "Dislocation climb controls creep. " + long),
                           ("Alloys", "The Cantor alloy CoCrFeMnNi is a high-entropy alloy. " + long),
                           ("RHEA", "Refractory HEAs such as NbMoTaW. " + long)], counts)
        self.assertEqual([p["section"] for p in out], ["Creep"])
        self.assertEqual(counts["dropped_hea"], 2)

    def test_text_records_use_only_passages_dated_before_the_cutoff(self) -> None:
        rec = {"record_id": "TXT::x", "source": "wikipedia", "doc": "d", "title": "t", "section": "s",
               "licence": "l", "url": "u", "text": "creep"}

        class Index:
            def top(self, text: str, n: int) -> list[dict[str, Any]]:
                return [{**rec, "record_id": "a", "date": "2023-12-31"}, {**rec, "record_id": "b", "date": None},
                        {**rec, "record_id": "c", "date": "2024-05-01"}]

        with patch.object(P._TextIndex, "get", classmethod(lambda cls: Index())):
            got = P.text_records("q", {"title": "t"}, "2024-03-01")
        self.assertEqual([r.record_id for r in got], ["a"])

    def test_generator_prompt_is_not_a_judge_prompt(self) -> None:
        import diag_analysis as D
        import rq_judge as RQ
        for system in (P.GENERATOR_SYSTEM, P.CRITIC_SYSTEM, P.NARROW_SYSTEM):
            self.assertNotIn(D.QUALITY_PAIR_SYSTEM[:80], system)
            self.assertNotIn(RQ.RQ_SYSTEM[:80], system)
        self.assertIn("3 items", P.GENERATOR_SYSTEM.replace("{k}", "3"))


if __name__ == "__main__":
    unittest.main()
