"""Tests for experiment 42 (loop.md 23.1): citation-filter repair, the v2 writer, retrieval v2, the payload with titles,
measurement v2 and the stage_v2 helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import hypo_loop as H
import judge_v2 as J2
import loop_methods as LM
import stage_v2 as S
from temporal_hypothesis_benchmark import RetrievalRecord

CASE = {"paper_id": "PMCT", "publication_date": "2024-06-01", "split": "validation",
        "queries": {lvl: {"text": "State one hypothesis with supporting evidence: improve the oxidation resistance of "
                                  "cast HfNbTaTiZr at 1000 C through a silicide coating mechanism."}
                    for lvl in ("broad", "problem_constrained", "expert_context")},
        "hidden_target": {"intervention": "Ink-extrusion three-dimensional printing followed by a slurry silicide coating"}}


def rec(i: int, text: str, kind: str = "web:Results", title: str = "A study") -> RetrievalRecord:
    return RetrievalRecord(f"P{i}::web::{i:03d}::x", f"P{i}", "2020-01-01", kind, text,
                           {"source": "web", "title": title})


def pool(kind: str) -> list[RetrievalRecord]:
    generic = [rec(i, "hypothesis evidence hypothesis evidence mechanism outcome " * 30) for i in range(5)]
    topical = [rec(10 + i, "silicide coating oxidation HfNbTaTiZr scale growth " * 30, title="Silicide coatings")
               for i in range(5)]
    filler = [rec(20 + i, "creep deformation of nickel superalloys " * 30) for i in range(60)]
    return generic + topical + filler


class Responder:
    def __init__(self, cite: list[str] | None = None) -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.cite = cite or []

    def __call__(self, harness, role, model, system, payload, max_out=None):
        self.calls.append((role, system, payload))
        return {"hypothesis": "A silicide coating protects the alloy.", "intervention": "silicide coating",
                "supporting_evidence_ids": list(self.cite), "conflicting_evidence_ids": []}


def run(method: str, responder: Responder) -> tuple[H.Harness, dict]:
    h = H.Harness(CASE, "broad", 1)
    with patch.object(h, "pool", side_effect=pool), patch.object(H.Harness, "ask", autospec=True, side_effect=responder):
        out = H.METHODS[method](h)
    return h, out


class RepairTests(unittest.TestCase):
    def test_filter_keeps_the_hypothesis_and_records_removed_ids(self) -> None:
        responder = Responder(cite=["P10::web::010::x", "made-up-id"])
        h, out = run("web64k_v2_b_o3mini", responder)
        self.assertEqual(len(responder.calls), 1)  # no regeneration
        self.assertEqual(out["citation_validation"], {"status": "filtered_unknown_ids",
                                                      "removed_unknown_ids": ["made-up-id"]})
        self.assertEqual(out["supporting_evidence_ids"], ["P10::web::010::x"])

    def test_default_still_regenerates(self) -> None:
        h = H.Harness(CASE, "broad", 1)
        answers = [{"hypothesis": "x", "supporting_evidence_ids": ["bad"]},
                   {"hypothesis": "y", "supporting_evidence_ids": []}]
        with patch.object(H.Harness, "ask", autospec=True, side_effect=lambda *a, **k: answers.pop(0)):
            out = h.generate_final("writer", "o3mini", "sys", {"query": "q"}, set())
        self.assertEqual(out["hypothesis"], "y")
        self.assertEqual(out["citation_validation"]["status"], "valid_after_regeneration")

    def test_filter_does_not_rescue_an_empty_hypothesis(self) -> None:
        h = H.Harness(CASE, "broad", 1)
        answers = [{"hypothesis": "", "supporting_evidence_ids": ["bad"]}, {"hypothesis": "z"}]
        with patch.object(H.Harness, "ask", autospec=True, side_effect=lambda *a, **k: answers.pop(0)):
            out = h.generate_final("writer", "o3mini", "sys", {"query": "q"}, set(), citation_repair="filter")
        self.assertEqual(out["hypothesis"], "z")


class WriterAndRetrievalTests(unittest.TestCase):
    def test_writer_v2_prompt(self) -> None:
        self.assertEqual(LM.WRITER_V2.count(LM.WRITER_V2_GUIDE), 1)
        self.assertEqual(LM.WRITER_V2.count(LM._RETURN), 1)
        self.assertTrue(LM.WRITER_V2.endswith(LM.WRITER_B.split(LM._RETURN)[1]))

    def test_closed_book_v2(self) -> None:
        responder = Responder()
        h, _ = run("writer_v2_b_o3mini", responder)
        self.assertEqual(responder.calls[0][1], LM.WRITER_V2)
        self.assertEqual(responder.calls[0][2]["eligible_evidence"], [])
        self.assertEqual(h.source, "fixed")

    def test_retrieval_v2_ignores_template_words_and_keeps_the_budget(self) -> None:
        responder = Responder()
        h, _ = run("web64k_r2_b_o3mini", responder)
        self.assertEqual(responder.calls[0][1], LM.WRITER_B)
        evidence = responder.calls[0][2]["eligible_evidence"]
        self.assertTrue(all(e["record_id"].startswith("P1") and int(e["record_id"][1:3]) >= 10 for e in evidence[:5]))
        self.assertEqual(evidence[0]["paper_title"], "Silicide coatings")
        self.assertEqual(evidence[0]["section"], "Results")
        total = sum(len(e["evidence"]) + len(e["paper_title"]) + len(e["section"]) for e in evidence)
        self.assertLessEqual(total, LM.R2_BUDGET)
        self.assertLessEqual(len(evidence), 96)
        cap = LM.rx.record_cap("text_chunks")
        self.assertTrue(all(len(e["evidence"]) + len(e["paper_title"]) + len(e["section"]) <= cap for e in evidence))
        self.assertEqual(h.source, "web")
        self.assertEqual(set(h.seen), {e["record_id"] for e in evidence})

    def test_combined_uses_both(self) -> None:
        responder = Responder()
        run("web64k_v2_b_o3mini", responder)
        self.assertEqual(responder.calls[0][1], LM.WRITER_V2)
        self.assertTrue(responder.calls[0][2]["eligible_evidence"])


class JudgeV2Tests(unittest.TestCase):
    def test_validate(self) -> None:
        good = {"scores": {d: 2 for d in J2.DIMENSIONS}, "rationale": {d: "x" for d in J2.DIMENSIONS}}
        self.assertEqual(J2.validate(good)["scores"]["outcome_agreement"], 2)
        for bad in ({"scores": {}}, {"scores": {**good["scores"], "outcome_agreement": 5}},
                    {"scores": {**good["scores"], "outcome_agreement": 1.5}},
                    {"scores": {**good["scores"], "outcome_agreement": True}}, "text"):
            with self.assertRaises(ValueError):
                J2.validate(bad)

    def test_blind_and_retry(self) -> None:
        gen = {"hypothesis": "h", "supporting_evidence_ids": ["E1"], "citation_validation": {}, "mechanism": "m"}
        self.assertEqual(J2.blind_hypothesis(gen), {"hypothesis": "h", "mechanism": "m"})
        answers = [{"scores": {"intervention_reconstruction": 9}},
                   {"scores": {d: 1 for d in J2.DIMENSIONS}, "rationale": {}}]
        with patch.object(J2.lc, "judge_chat_json", side_effect=lambda *a, **k: answers.pop(0)):
            out = J2.judge("gpt56", "q", {"intervention": "t"}, gen)
        self.assertEqual(out["scores"]["mechanism_agreement"], 1)
        self.assertEqual(out["rubric"], "v2-anchored-evidence-blind")
        self.assertNotIn("E1", J2.payload("q", {}, gen))


class StageHelperTests(unittest.TestCase):
    def test_clean_terms_drop_template_words(self) -> None:
        terms = S.clean_terms("State one hypothesis with supporting evidence on silicide coating oxidation")
        self.assertNotIn("hypothesis", terms)
        self.assertNotIn("evidence", terms)
        self.assertIn("silicide", terms)

    def test_classify_removed_citations(self) -> None:
        seen = ["PMC1::web::002::1_introduction", "PMC2::web::010::results"]
        kinds = S.classify_removed(["PMC1::web::002::introduction", "PMC1::web::002", "PMC2::web::011::results",
                                    "PMC9::web::000::abstract"], seen)
        self.assertEqual(kinds, {"pack record, section suffix rewritten": 2, "pack paper, record not in pack": 1,
                                 "paper not in pack": 1})

    def test_reverse_job_order(self) -> None:
        import os
        import tempfile
        from pathlib import Path

        import v2_analysis as VA
        runs = [{"method": "m", "run_id": f"r{i}", "status": "ok"} for i in range(4)]
        env = {k: v for k, v in os.environ.items() if k not in ("MATHG_PENDING_SHUFFLE", "MATHG_PENDING_REVERSE")}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, env, clear=True), \
                patch.object(H, "OUT", Path(tmp)), patch.object(H, "all_runs", return_value=runs):
            (Path(tmp) / "m" / "audit").mkdir(parents=True)
            (Path(tmp) / "m" / "audit" / "r1.json").write_text("{}")
            self.assertEqual([r["run_id"] for (r,) in H._pending(["m"], "audit")], ["r0", "r2", "r3"])
            self.assertEqual(VA._shuffle([1, 2, 3]), [1, 2, 3])
            os.environ["MATHG_PENDING_REVERSE"] = "1"
            self.assertEqual([r["run_id"] for (r,) in H._pending(["m"], "audit")], ["r3", "r2", "r0"])
            self.assertEqual(VA._shuffle([1, 2, 3]), [3, 2, 1])

    def test_gap_and_study(self) -> None:
        intro = ("Refractory alloys oxidise quickly. Coatings were tried before. Their adhesion is poor at high "
                 "temperature, and spallation limits their life in air. Little is known about silicide coatings on "
                 "these alloys. In this work, we deposit a silicide coating by slurry and test it at 1000 C.")
        out = S.gap_and_study([("Abstract", "x"), ("1. Introduction", intro)])
        self.assertTrue(out["gap"].startswith("Refractory"))
        self.assertTrue(out["study"].startswith("In this work"))
        self.assertIsNone(S.gap_and_study([("Methods", intro)]))


if __name__ == "__main__":
    unittest.main()
