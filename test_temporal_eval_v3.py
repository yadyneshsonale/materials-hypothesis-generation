from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import llm_client
from temporal_hypothesis_benchmark import RetrievalRecord
from temporal_eval_v3 import (
    ALL_DIMENSIONS,
    PAIRS,
    QUERY_LEVELS,
    SETTINGS,
    EligibleCorpus,
    analyze,
    build_corpus,
    cluster_bootstrap,
    eligible_ids,
    exact_sign_test,
    holm_adjust,
    query_leak,
    resolve_pair,
    run_tool_agent,
)


def _metadata() -> dict[str, dict[str, object]]:
    return {
        "T": {"earliest_public_date": "2021-03-01", "work_family_id": "fam-T", "title": "Target paper title here", "doi": "10.1/target"},
        "A": {"earliest_public_date": "2015-05-01", "work_family_id": "fam-A", "title": "Earlier alloy paper"},
        "B": {"earliest_public_date": "2020-01-01", "work_family_id": "fam-T", "title": "Same family as target"},
        "C": {"earliest_public_date": "2022-01-01", "work_family_id": "fam-C", "title": "Future paper"},
    }


class _FakeUnit:
    def __init__(self, unit_id: str, paper_id: str) -> None:
        self.unit_id = unit_id
        self.paper_id = paper_id

    def to_dict(self) -> dict[str, object]:
        return {"unit_id": self.unit_id, "paper_id": self.paper_id, "measurements": []}


class TemporalEvalV3Tests(unittest.TestCase):
    def test_eligibility_excludes_target_future_and_same_family(self) -> None:
        self.assertEqual(eligible_ids(_metadata(), "T", "2021-03-01"), {"A"})

    def test_build_corpus_keeps_only_eligible_chunks_and_units(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            maps = Path(directory)
            for pid in ("A", "B", "C", "T"):
                (maps / f"{pid}.json").write_text(json.dumps({"chunks": [{
                    "chunk_id": f"{pid}::chunk::000", "section": "Results", "chunk_index": 0,
                    "text": f"alloy text from {pid}",
                }]}))
            eligible, chunks, units = build_corpus(
                "T", "2021-03-01", _metadata(),
                [_FakeUnit("A::unit", "A"), _FakeUnit("B::unit", "B"), _FakeUnit("C::unit", "C")],
                maps,
            )
        self.assertEqual(eligible, {"A"})
        self.assertEqual([r.paper_id for r in chunks], ["A"])
        self.assertEqual([r.paper_id for r in units], ["A"])
        self.assertTrue(all(r.publication_date < "2021-03-01" for r in chunks + units))

    def test_tool_corpus_search_and_read_enforce_eligibility(self) -> None:
        record = RetrievalRecord("A::c1", "A", "2015-05-01", "chunk:Results",
                                 "alpha beta gamma delta epsilon", {})
        corpus = EligibleCorpus(_metadata(), {"A"}, [record])
        found = corpus.search("alpha beta")
        self.assertEqual([row["record_id"] for row in found["results"]], ["A::c1"])
        self.assertIn("A::c1", corpus.seen_ids)
        self.assertNotIn("A::c1", corpus.read_ids)
        self.assertIn("error", corpus.read("T::unknown"))
        page = corpus.read("A::c1")
        self.assertIsNone(page["next_offset"])
        self.assertIn("A::c1", corpus.read_ids)
        self.assertEqual(corpus.list_papers()["papers"][0]["paper_id"], "A")

    def test_tool_agent_requires_reading_before_citing(self) -> None:
        record = RetrievalRecord("A::c1", "A", "2015-05-01", "chunk:Results",
                                 "alpha beta gamma delta epsilon", {})
        corpus = EligibleCorpus(_metadata(), {"A"}, [record])
        hypothesis = {
            "hypothesis": "Alloying with alpha raises strength.",
            "supporting_evidence_ids": ["A::c1"],
            "conflicting_evidence_ids": [],
        }
        script = [
            ("search_corpus", {"query": "alpha beta"}),
            ("submit_hypothesis", {"hypothesis": hypothesis}),
            ("read_record", {"record_id": "A::c1"}),
            ("submit_hypothesis", {"hypothesis": hypothesis}),
        ]
        turns = iter(script)

        def fake_model(messages, tools):
            name, args = next(turns)
            return {"content": "", "tool_calls": [{
                "id": f"call_{name}_{len(messages)}", "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }]}

        result = run_tool_agent("query", "2021-03-01", corpus, call_model=fake_model)
        self.assertEqual(result["generation"]["supporting_evidence_ids"], ["A::c1"])
        self.assertEqual(result["tool_calls"], 2)
        rejected = [step for step in result["trace"] if step.get("accepted") is False]
        self.assertEqual(len(rejected), 1)
        self.assertIn("A::c1", corpus.read_ids)

    def test_judge_routes_to_trapi_gpt56_without_temperature(self) -> None:
        captured: dict[str, object] = {}

        class _Response:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {"choices": [{"finish_reason": "stop", "message": {"content": '{"ok": true}'}}]}

        def fake_post(url, headers=None, json=None, timeout=None):  # noqa: A002
            captured["url"] = url
            captured["payload"] = json
            return _Response()

        env = {k: v for k, v in os.environ.items() if k != "JUDGE_PROVIDER"}
        with patch.dict(os.environ, env, clear=True), \
                patch.object(llm_client, "_trapi_token", return_value="token"), \
                patch.object(llm_client.requests, "post", side_effect=fake_post):
            result = llm_client.judge_chat_json("system", "user")
        self.assertEqual(result, {"ok": True})
        self.assertIn("gpt-5.6-sol_2026-07-09", str(captured["url"]))
        self.assertIn("max_completion_tokens", captured["payload"])
        self.assertNotIn("temperature", captured["payload"])
        self.assertEqual(llm_client.judge_info(), f"trapi:{llm_client.JUDGE_TRAPI_DEPLOYMENT}")

    def test_pair_resolution_requires_both_orders_to_agree(self) -> None:
        self.assertEqual(resolve_pair("x", "y", {"winner": "A"}, {"winner": "B"}), ("x", "consistent"))
        self.assertEqual(resolve_pair("x", "y", {"winner": "A"}, {"winner": "A"}), ("tie", "position_inconsistent"))
        self.assertEqual(resolve_pair("x", "y", {"winner": "TIE"}, {"winner": "TIE"}), ("tie", "consistent"))

    def test_tool_budget_is_enforced_per_call_within_a_batch(self) -> None:
        record = RetrievalRecord("A::c1", "A", "2015-05-01", "chunk:Results",
                                 "alpha beta gamma delta epsilon", {})
        corpus = EligibleCorpus(_metadata(), {"A"}, [record])
        hypothesis = {"hypothesis": "Alloying with alpha raises strength.",
                      "supporting_evidence_ids": [], "conflicting_evidence_ids": []}
        batch = [{"id": f"call_{index}", "type": "function",
                  "function": {"name": "list_papers", "arguments": "{}"}} for index in range(3)]
        replies = iter([
            {"content": "", "tool_calls": batch},
            {"content": "", "tool_calls": [{"id": "submit", "type": "function", "function": {
                "name": "submit_hypothesis", "arguments": json.dumps({"hypothesis": hypothesis})}}]},
        ])

        with patch("temporal_eval_v3.MAX_TOOL_CALLS", 2):
            result = run_tool_agent("query", "2021-03-01", corpus, call_model=lambda messages, tools: next(replies))
        self.assertEqual(result["tool_calls"], 2)
        refused = [step for step in result["trace"] if step.get("refused") == "budget_exhausted"]
        self.assertEqual(len(refused), 1)

    def test_statistics_helpers(self) -> None:
        p_value, positive, negative = exact_sign_test([1.0, 1.0, 1.0, 1.0, -1.0])
        self.assertAlmostEqual(p_value, 0.375)
        self.assertEqual((positive, negative), (4, 1))
        first = cluster_bootstrap({"P1": [1.0], "P2": [1.0], "P3": [1.0]})
        self.assertEqual(first, (1.0, 1.0, 1.0))
        self.assertEqual(cluster_bootstrap({"P1": [0.5, 1.5], "P2": [2.0]}),
                         cluster_bootstrap({"P1": [0.5, 1.5], "P2": [2.0]}))

    def test_query_leak_detects_doi_and_title(self) -> None:
        row = {"doi": "10.1/target", "title": "Target paper title here for testing"}
        self.assertTrue(query_leak("see 10.1/target for details", row))
        self.assertTrue(query_leak("the target paper title here for testing matters", row))
        self.assertFalse(query_leak("alloy strength at high temperature", row))

    def _write_fixture(self, root: Path) -> tuple[Path, Path]:
        cases = root / "cases"
        out = root / "eval"
        cases.mkdir()
        (cases / "PMCT.json").write_text(json.dumps({"paper_id": "PMCT", "publication_date": "2021-03-01"}))
        for subdirectory in ("runs", "judgments/absolute", "judgments/pairwise"):
            (out / subdirectory).mkdir(parents=True)
        for level in QUERY_LEVELS:
            for index, setting in enumerate(SETTINGS):
                run_id = f"PMCT__{level}__{setting}"
                (out / "runs" / f"{run_id}.json").write_text(json.dumps({
                    "run_id": run_id, "paper_id": "PMCT", "query_level": level, "setting": setting,
                    "status": "ok", "generator": "openai:fake-model",
                    "tool_calls": 3 if setting == "tool_agent" else 0, "turns": 2,
                    "accessed_record_ids": ["A::c1"], "cited_evidence_ids": ["A::c1"],
                    "elapsed_seconds": 1.0,
                    "audit": {"temporal_violations": 0, "test_paper_leaks": 0, "family_leaks": 0,
                              "unknown_record_ids": 0, "invalid_citations": 0, "query_leak": 0},
                }))
                scores = {dim: 2 + index for dim in ALL_DIMENSIONS}
                (out / "judgments" / "absolute" / f"{run_id}.json").write_text(json.dumps({
                    "run_id": run_id, "scores": scores, "classification": "partial_reconstruction",
                    "judge": "trapi:fake-judge",
                }))
        for level in QUERY_LEVELS:
            for first, second in PAIRS:
                (out / "judgments" / "pairwise" / f"PMCT__{level}__{first}__vs__{second}.json").write_text(json.dumps({
                    "paper_id": "PMCT", "query_level": level, "setting_a": first, "setting_b": second,
                    "outcome": first, "consistency": "consistent", "judge": "trapi:fake-judge",
                }))
        return cases, out

    def test_analyze_integrity_on_a_complete_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cases, out = self._write_fixture(Path(directory))
            analysis = analyze(cases_dir=cases, output_dir=out)
            integrity = analysis["integrity"]
            self.assertTrue(integrity["verified"])
            self.assertEqual(integrity["expected_runs"], 12)
            self.assertEqual(integrity["pairs_judged"], 9)
            self.assertEqual(integrity["generators"], ["openai:fake-model"])
            self.assertEqual(integrity["judges"], ["trapi:fake-judge"])
            self.assertAlmostEqual(analysis["by_setting"]["tool_agent"]["reconstruction_mean"], 5.0)
            primary = {(item["a"], item["b"]): item for item in analysis["comparisons"] if item["role"] == "primary"}
            self.assertAlmostEqual(primary[("tool_agent", "closed_book")]["mean_difference"], 3.0)
            self.assertIn("holm_adjusted_p", primary[("tool_agent", "closed_book")])
            self.assertTrue((out / "results" / "summary.md").exists())

    def test_analyze_fails_integrity_for_missing_pairs_or_mixed_generators(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cases, out = self._write_fixture(Path(directory))
            (out / "judgments" / "pairwise" / "PMCT__broad__tool_agent__vs__closed_book.json").unlink()
            self.assertFalse(analyze(cases_dir=cases, output_dir=out)["integrity"]["verified"])
        with tempfile.TemporaryDirectory() as directory:
            cases, out = self._write_fixture(Path(directory))
            run_path = out / "runs" / "PMCT__broad__closed_book.json"
            payload = json.loads(run_path.read_text())
            payload["generator"] = "openai:other-model"
            run_path.write_text(json.dumps(payload))
            self.assertFalse(analyze(cases_dir=cases, output_dir=out)["integrity"]["verified"])

    def test_holm_adjustment_matches_step_down_rule(self) -> None:
        for got, expected in zip(holm_adjust([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06]):
            self.assertAlmostEqual(got, expected)


if __name__ == "__main__":
    unittest.main()
