from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import llm_client
from temporal_eval_critique import (
    CRITIC_PAYLOAD_KEYS,
    CRITICS,
    check_model_cutoffs,
    assert_no_target_records,
    assert_payload,
    analyze_trace,
    blind_for_critics,
    revise_run,
    run_reviser,
    validate_findings,
)
from temporal_hypothesis_benchmark import RetrievalRecord


def _hypothesis(supporting: list[str]) -> dict[str, object]:
    return {
        "hypothesis": "Adding Al raises strength.", "material_initial_state": "HfMoTaTiZr",
        "intervention": "Add 5 at.% Al", "conditions": "Anneal 900 C", "structural_mediator": "B2 precipitates",
        "mechanism": "Orowan bypass", "predicted_outcome": "Yield above 1 GPa", "baseline": "HfMoTaTiZr",
        "boundary": "Above 5 at.%", "uncertainty": "Limited data", "supporting_evidence_ids": supporting,
        "conflicting_evidence_ids": [], "falsification_experiment": "Measure yield after anneal",
    }


class LeakageGuardTests(unittest.TestCase):
    def test_hidden_target_is_never_allowed_in_a_payload(self) -> None:
        payload = {"query": "q", "knowledge_cutoff": "2024-01-02", "hypothesis": {}, "evidence": [],
                   "hidden_target": {"intervention": "secret"}}
        with self.assertRaises(ValueError):
            assert_payload(payload, CRITIC_PAYLOAD_KEYS)

    def test_hidden_target_text_hidden_inside_allowed_field_is_rejected(self) -> None:
        payload = {"query": "q", "knowledge_cutoff": "2024-01-02", "hypothesis": {"note": "hidden_target leaked"},
                   "evidence": []}
        with self.assertRaises(ValueError):
            assert_payload(payload, CRITIC_PAYLOAD_KEYS)

    def test_unexpected_payload_keys_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            assert_payload({"query": "q", "knowledge_cutoff": "x", "hypothesis": {}, "evidence": [],
                            "doi": "10.1/t"}, CRITIC_PAYLOAD_KEYS)

    def test_target_and_family_records_are_rejected(self) -> None:
        metadata = {"T": {"work_family_id": "fam-T"}, "A": {"work_family_id": "fam-A"},
                    "P": {"work_family_id": "fam-T"}}
        case = {"paper_id": "T"}
        lookup = {
            "A::c1": RetrievalRecord("A::c1", "A", "2019-01-01", "chunk:Results", "alpha", {}),
            "T::c1": RetrievalRecord("T::c1", "T", "2019-01-01", "chunk:Results", "beta", {}),
            "P::c1": RetrievalRecord("P::c1", "P", "2019-01-01", "chunk:Results", "gamma", {}),
        }
        assert_no_target_records(["A::c1"], lookup, case, metadata)
        with self.assertRaises(ValueError):
            assert_no_target_records(["T::c1"], lookup, case, metadata)
        with self.assertRaises(ValueError):
            assert_no_target_records(["P::c1"], lookup, case, metadata)

    def test_late_model_cutoff_is_rejected(self) -> None:
        check_model_cutoffs("2024-01-02")
        with self.assertRaises(ValueError):
            check_model_cutoffs("2023-12-31")

    def test_every_chosen_model_predates_the_earliest_held_out_paper(self) -> None:
        for model in CRITICS:
            self.assertLess(model["knowledge_cutoff"], "2024-01-02", model["deployment"])

    def test_blinding_hides_record_ids_from_critics(self) -> None:
        lookup = {"A::c1": RetrievalRecord("A::c1", "A", "2019-01-01", "chunk:Results", "alpha", {})}
        hypothesis, evidence, labels = blind_for_critics(_hypothesis(["A::c1"]), ["A::c1"], lookup)
        text = json.dumps({"hypothesis": hypothesis, "evidence": evidence})
        self.assertNotIn("A::c1", text)
        self.assertEqual(labels["A::c1"], "E1")
        self.assertEqual(hypothesis["supporting_evidence_ids"], ["E1"])


class CritiqueLogicTests(unittest.TestCase):
    def test_findings_are_validated_and_clamped(self) -> None:
        findings = validate_findings({"findings": [
            {"claim": "c", "issue_type": "weird", "severity": 9, "evidence_ids": ["E2", "A::c1"],
             "explanation": "e", "suggested_fix": "f"},
            "not a dict",
        ]})
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue_type"], "other")
        self.assertEqual(findings[0]["severity"], 3)
        self.assertEqual(findings[0]["evidence_labels"], ["E2"])
        with self.assertRaises(ValueError):
            validate_findings({"not_findings": []})

    def test_trace_analysis_counts_reads_searches_and_rejections(self) -> None:
        run = {
            "tool_calls": 4, "cited_evidence_ids": ["A::c1", "B::c2"],
            "tool_trace": [
                {"tool": "search_corpus", "args": {"query": "hf", "k": 5}},
                {"tool": "search_corpus", "args": {"query": "hf", "k": 5}},
                {"tool": "read_record", "args": {"record_id": "A::c1"}},
                {"tool": "submit_hypothesis", "accepted": False},
                {"tool": "submit_hypothesis", "accepted": True},
                {"tool": "list_papers", "args": {}, "refused": "budget_exhausted"},
            ],
        }
        stats = analyze_trace(run)
        self.assertEqual(stats["searches"], 2)
        self.assertEqual(stats["repeated_searches"], 1)
        self.assertEqual(stats["reads"], 1)
        self.assertEqual(stats["rejected_submissions"], 1)
        self.assertEqual(stats["refused_calls"], 1)
        self.assertEqual(stats["cited_but_unread"], 1)
        self.assertEqual(stats["read_but_uncited"], 0)

    def _base_run(self) -> tuple[dict, dict, dict]:
        lookup = {"A::c1": RetrievalRecord("A::c1", "A", "2019-01-01", "chunk:Results", "alpha beta", {})}
        base = {
            "run_id": "PMCT__broad__tool_agent", "paper_id": "PMCT", "query_level": "broad", "query": "q",
            "publication_date": "2024-01-02", "accessed_record_ids": ["A::c1"], "cited_evidence_ids": ["A::c1"],
            "generation": _hypothesis(["A::c1"]), "tool_calls": 2,
            "tool_trace": [{"tool": "read_record", "args": {"record_id": "A::c1"}}],
        }
        case = {"paper_id": "PMCT", "hidden_target": {"intervention": "x"}}
        metadata = {"PMCT": {"work_family_id": "fam-T"}, "A": {"work_family_id": "fam-A"}}
        return base, {"lookup": lookup}, {"case": case, "metadata": metadata}

    def test_reviser_repairs_an_invalid_citation_once(self) -> None:
        responses = [
            {"hypothesis": _hypothesis(["ZZ::fake"])},
            {"hypothesis": _hypothesis(["A::c1"])},
        ]
        lookup = {"A::c1": RetrievalRecord("A::c1", "A", "2019-01-01", "chunk:Results", "alpha", {})}
        with patch("temporal_eval_critique.trapi_chat_json", side_effect=responses):
            result = run_reviser("q", "2024-01-02", _hypothesis(["A::c1"]), ["A::c1"], lookup, [], "self")
        self.assertEqual(result["status"], "revised_after_repair")
        self.assertEqual(result["generation"]["supporting_evidence_ids"], ["A::c1"])

    def test_reviser_falls_back_to_the_original_when_citations_stay_invalid(self) -> None:
        bad = {"hypothesis": _hypothesis(["ZZ::fake"])}
        lookup = {"A::c1": RetrievalRecord("A::c1", "A", "2019-01-01", "chunk:Results", "alpha", {})}
        with patch("temporal_eval_critique.trapi_chat_json", side_effect=[bad, bad]):
            result = run_reviser("q", "2024-01-02", _hypothesis(["A::c1"]), ["A::c1"], lookup, [], "self")
        self.assertEqual(result["status"], "fallback_original")
        self.assertEqual(result["generation"]["supporting_evidence_ids"], ["A::c1"])

    def test_critique_arm_does_not_revise_when_a_critic_fails(self) -> None:
        from llm_client import LLMError
        base, context, extra = self._base_run()
        ok_findings = [{"claim": "c", "issue_type": "unsupported", "severity": 1, "evidence_labels": [],
                        "explanation": "", "suggested_fix": ""}]

        def fake_critic(model, *args, **kwargs):
            if model["role"] == "consistency":
                raise LLMError("boom")
            return ok_findings

        with patch("temporal_eval_critique.run_critic", side_effect=fake_critic), \
                patch("temporal_eval_critique.run_reviser") as reviser, \
                patch("temporal_eval_critique.analyze_trace", return_value={}):
            record = revise_run(base, "critique", extra["case"], context, extra["metadata"])
        self.assertEqual(record["status"], "critic_incomplete")
        reviser.assert_not_called()
        self.assertFalse(record["payload_audit"]["hidden_target_sent"])

    def test_self_revise_arm_runs_with_no_critics(self) -> None:
        base, context, extra = self._base_run()
        from temporal_eval_critique import REVISER
        reply = {"hypothesis": _hypothesis(["A::c1"])}
        with patch("temporal_eval_critique.run_critic") as critic, \
                patch("temporal_eval_critique.trapi_chat_json", return_value=reply) as call:
            record = revise_run(base, "self_revise", extra["case"], context, extra["metadata"])
        critic.assert_not_called()
        self.assertEqual(record["status"], "ok")
        self.assertEqual(call.call_args.args[0], REVISER["deployment"])
        self.assertEqual(record["payload_audit"]["hidden_target_sent"], False)


class TrapiRefactorTests(unittest.TestCase):
    def test_trapi_call_uses_named_deployment_and_token_field(self) -> None:
        captured = {}

        class _Resp:
            status_code = 200
            text = ""

            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {"choices": [{"finish_reason": "stop", "message": {"content": '{"ok": true}'}}]}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            return _Resp()

        with patch("llm_client._trapi_token", return_value="t"), patch("llm_client.requests.post", side_effect=fake_post):
            out = llm_client.trapi_chat_json("Llama-3.3-70B-Instruct_5", "s", "u", max_tokens=100,
                                             token_field="max_tokens", temperature=0.0, retries=1)
        self.assertEqual(out, {"ok": True})
        self.assertIn("/deployments/Llama-3.3-70B-Instruct_5/", captured["url"])
        self.assertEqual(captured["json"]["max_tokens"], 100)
        self.assertEqual(captured["json"]["temperature"], 0.0)
        self.assertNotIn("max_completion_tokens", captured["json"])


if __name__ == "__main__":
    unittest.main()
