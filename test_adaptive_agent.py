from __future__ import annotations

import json
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from adaptive_agent import (
    EvidenceItem,
    Task,
    _evidence_text,
    retrieve_cited_role_evidence,
    retrieve_evidence,
    run_workflow,
)
from build_evidence_graph import _deterministic_annotations, _external_citations, _validate_bundle, build_paper
from evidence_model import EvidenceEntity, EvidenceRelation, index_relations, load_relations
from graph_build import Graph, Node
from source_context import build_source_bundle, load_context_index


class EvidenceRelationTests(unittest.TestCase):
    def test_explicit_missing_relation_file_fails(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_relations(Path("does-not-exist.jsonl"))

    def test_rejects_unknown_relation_type(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown relation_type"):
            EvidenceRelation.from_dict({
                "relation_id": "R1",
                "relation_type": "beats",
                "source_entity_id": "A",
                "target_entity_ids": ["B"],
            })

    def test_typed_relation_expands_retrieval(self) -> None:
        source = Node("A", "paper-a", "causal_claim", "Lithium interface stability", [], {"lithium", "interface", "stability"})
        target = Node("B", "paper-b", "evidence_result", "A distinct measured comparison", [], {"measured", "comparison"})
        graph = Graph(nodes={"A": source, "B": target}, edges={"A": [], "B": []})
        relation = EvidenceRelation(
            relation_id="R1",
            relation_type="outperforms",
            source_entity_id="A",
            target_entity_ids=["B"],
            source_paper_id="paper-a",
            evidence_span="Method A outperformed method B.",
            metric="stability",
            confidence=0.9,
        )

        evidence = retrieve_evidence(
            Task("T1", "How can lithium interface stability improve?", "mechanism"),
            graph,
            index_relations([relation]),
        )

        retrieved = {item.node_id: item for item in evidence}
        self.assertIn("A", retrieved)
        self.assertIn("B", retrieved)
        self.assertEqual(retrieved["B"].retrieval_reason, "typed_relation:outperforms:R1")

    def test_typed_entity_is_a_retrieval_seed(self) -> None:
        entity = EvidenceEntity(
            entity_id="material:lpscl",
            entity_type="material_system",
            name="Li6PS5Cl argyrodite",
            description="solid electrolyte interface material",
            source_paper_id="paper-a",
            evidence_span="Li6PS5Cl solid electrolyte",
        )
        evidence = retrieve_evidence(
            Task("T1", "Which argyrodite solid electrolyte is relevant?", "materials"),
            Graph({}, {}),
            entity_index={entity.entity_id: entity},
        )

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].node_id, entity.entity_id)
        self.assertEqual(evidence[0].retrieval_reason, "typed_entity_seed")


class WorkflowRoutingTests(unittest.TestCase):
    def test_cited_roles_become_first_class_evidence(self) -> None:
        source = EvidenceItem(
            "table:1", "paper-1", "table_context", "Capacity retention", [], 2.0, "table_seed",
            source_contexts=[{
                "citations": [{
                    "reference_id": "reference:2",
                    "reference_number": "2",
                    "resolved_paper_id": "paper-2",
                    "resolution_method": "title",
                    "cited_role_context": [{
                        "claim_id": "paper-2::evidence_result::0",
                        "role": "evidence_result",
                        "content": "The coated interface retained 92 percent capacity.",
                        "evidence_spans": ["Capacity retention reached 92 percent."],
                        "relevance_score": 3,
                    }],
                }],
            }],
        )
        task = Task("T1", "Which coating improves capacity retention?", "evidence", required_roles=["evidence_result"])

        cited = retrieve_cited_role_evidence(task, [source])

        self.assertEqual([item.node_id for item in cited], ["paper-2::evidence_result::0"])
        self.assertEqual(cited[0].retrieval_reason, "cited_role:table:1:reference:2")
        self.assertIn("CITATION PROVENANCE", _evidence_text(cited[0]))

    def test_workflow_allows_synthesis_to_cite_promoted_role(self) -> None:
        source = EvidenceItem(
            "table:1", "paper-1", "table_context", "Capacity retention", [], 2.0, "table_seed",
            source_contexts=[{"citations": [{
                "reference_id": "reference:2",
                "reference_number": "2",
                "resolved_paper_id": "paper-2",
                "resolution_method": "title",
                "cited_role_context": [{
                    "claim_id": "paper-2::evidence_result::0",
                    "role": "evidence_result",
                    "content": "The coated interface retained 92 percent capacity.",
                    "evidence_spans": ["Capacity retention reached 92 percent."],
                    "relevance_score": 3,
                }],
            }]}],
        )
        task = Task("T1", "Which coating improves retention?", "evidence", required_roles=["evidence_result"])
        assessment = {
            "decision": "sufficient",
            "finding": "The coating improved retention.",
            "cited_ids": ["paper-2::evidence_result::0"],
            "reason": "Direct cited-paper evidence.",
            "missing_questions": [],
            "assumptions": [],
        }
        candidate = {"hypothesis": "Use the coating.", "cited_ids": ["paper-2::evidence_result::0"]}
        with TemporaryDirectory() as directory:
            trace_path = Path(directory) / "trace.json"
            with (
                patch("adaptive_agent.build_graph", return_value=Graph({}, {})),
                patch("adaptive_agent.decompose_goal", return_value=[task]),
                patch("adaptive_agent.retrieve_evidence", return_value=[source]),
                patch("adaptive_agent.assess_sufficiency", return_value=assessment),
                patch("adaptive_agent.adjudicate_conflicts", return_value={"conflicts": []}),
                patch("adaptive_agent.synthesize", return_value=[candidate]),
                patch("adaptive_agent.critique", return_value={}),
            ):
                result = run_workflow("goal", Path(directory), trace_path)

        citation_event = next(event for event in result["events"] if event["stage"] == "citation_augmentation")
        self.assertEqual(result["subagents"], [
            "planner_orchestrator",
            "evidence_researcher",
            "evidence_adjudicator",
            "hypothesis_synthesizer",
            "critic",
        ])
        self.assertEqual(citation_event["resolved_claims"][0]["node_id"], "paper-2::evidence_result::0")
        self.assertEqual(result["candidates"][0]["cited_ids"], ["paper-2::evidence_result::0"])

    def test_missing_constraint_uses_autonomous_assumption_and_does_not_block_synthesis(self) -> None:
        tasks = [
            Task("T1", "Which operating temperature should be used?", "constraints"),
            Task("T2", "Find mechanisms at that temperature.", "mechanisms", ["T1"]),
        ]
        assessment = {
            "decision": "reason_with_caveat",
            "finding": "A conservative ambient temperature is assumed.",
            "cited_ids": [],
            "reason": "No operating temperature was supplied.",
            "missing_questions": [],
            "assumptions": ["Assume ambient operation at 25 C."],
        }
        with TemporaryDirectory() as directory:
            trace_path = Path(directory) / "trace.json"
            with (
                patch("adaptive_agent.build_graph", return_value=Graph({}, {})),
                patch("adaptive_agent.decompose_goal", return_value=tasks),
                patch("adaptive_agent.retrieve_evidence", return_value=[]),
                patch("adaptive_agent.assess_sufficiency", return_value=assessment),
                patch("adaptive_agent.adjudicate_conflicts", return_value={"conflicts": []}),
                patch("adaptive_agent.synthesize", return_value=[]) as synthesize,
            ):
                result = run_workflow("goal", Path(directory), trace_path)

        self.assertEqual(result["status"], "complete_without_candidates")
        self.assertEqual(result["tasks"][0]["decision"], "reason_with_caveat")
        self.assertEqual(result["tasks"][1]["status"], "complete")
        self.assertEqual(result["events"][-1]["stage"], "synthesis")
        self.assertEqual(result["tasks"][0]["assumptions"], ["Assume ambient operation at 25 C."])
        synthesize.assert_called_once()


class EvidenceGraphBuilderTests(unittest.TestCase):
    def test_external_citations_are_canonicalized_by_identifier(self) -> None:
        entities, relations = _external_citations(
            "2604.00001",
            "Introduction\nReferences\narXiv:2402.00729 and https://arxiv.org/abs/2402.00729\n"
            "doi:10.1145/2939672.2939785\n",
        )

        self.assertEqual({entity.entity_id for entity in entities}, {
            "paper:arxiv:2402.00729",
            "paper:doi:10.1145/2939672.2939785",
        })
        self.assertEqual(len(relations), 2)
        self.assertTrue(all(relation.relation_type == "cites" for relation in relations))

    def test_negated_outperformance_is_a_nondirectional_comparison(self) -> None:
        claims = [
            {
                "claim_id": "claim:baseline",
                "role": "prior_approach",
                "content": "The baseline uses separated design.",
                "evidence": "The baseline uses separated design.",
            },
            {
                "claim_id": "claim:result",
                "role": "evidence_result",
                "content": "The proposed method does not beat the baseline.",
                "evidence": "The proposed method does not outperform the baseline.",
            },
        ]

        _, relations = _deterministic_annotations("paper-1", claims)
        relation_types = {relation.relation_type for relation in relations}

        self.assertIn("compares_with", relation_types)
        self.assertNotIn("outperforms", relation_types)

    def test_source_context_anchors_fallback_claims_and_cited_table_comparisons(self) -> None:
        record = {
            "paper_id": "paper-1",
            "reconciled_by_role": {
                "evidence_result": [{
                    "content": "The new method exceeds the baseline.",
                    "evidence_span": "The new method exceeds the baseline [2].",
                }],
            },
        }
        text = (
            "Results\n"
            "The new method exceeds the baseline [2].\n\n"
            "TABLE I. Retention compared with previous work\n"
            "Method  Retention\nNew  92\nBaseline  74\n\n"
            "References\n[2] A. Smith, Baseline electrolyte method, Journal 1, 10 (2025).\n"
        )

        bundle = build_source_bundle("paper-1", text, record)

        self.assertIn("paper-1::evidence_result::0", bundle["claim_passage_ids"])
        comparisons = [row for row in bundle["comparison_contexts"] if row["cross_paper"]]
        self.assertEqual(len(comparisons), 1)
        self.assertEqual(comparisons[0]["cited_references"][0]["reference_number"], "2")
        self.assertEqual(comparisons[0]["cited_content_status"], "requires_resolution")
        with TemporaryDirectory() as directory:
            paper_dir = Path(directory) / "papers"
            paper_dir.mkdir()
            (paper_dir / "paper-1.json").write_text(json.dumps(bundle))
            context_index = load_context_index(Path(directory))

        self.assertIn(comparisons[0]["comparison_id"], context_index)
        self.assertIn(bundle["tables"][0]["table_id"], context_index)

    def test_table_citation_includes_relevant_roles_from_resolved_local_paper(self) -> None:
        base_record = {"paper_id": "paper-1", "reconciled_by_role": {}}
        cited_record = {
            "paper_id": "paper-2",
            "reconciled_by_role": {
                "evidence_result": [{
                    "content": "The coated interface retained 92 percent capacity.",
                    "evidence_spans": ["Capacity retention reached 92 percent."],
                }],
                "mechanism_principle": [{
                    "content": "The coating suppresses interfacial decomposition.",
                    "evidence_spans": ["The coating suppressed decomposition."],
                }],
            },
        }
        text = (
            "Results\nTABLE 1. Capacity retention compared with prior work [2]\n"
            "Coated 92\nBaseline 74\n\nReferences\n"
            "[2] A. Smith, Coated interfaces for stable batteries, Journal (2025).\n"
        )

        bundle = build_source_bundle(
            "paper-1",
            text,
            base_record,
            {"paper-1": base_record, "paper-2": cited_record},
            {"paper-2": {"title": "Coated interfaces for stable batteries"}},
        )
        citation = bundle["tables"][0]["citations"][0]

        self.assertEqual(citation["resolved_paper_id"], "paper-2")
        self.assertEqual(citation["resolution_status"], "local_extraction_available")
        self.assertEqual(citation["cited_role_context"][0]["role"], "evidence_result")
        self.assertEqual(bundle["comparison_contexts"][0]["cited_content_status"], "local_extraction_available")
        with TemporaryDirectory() as directory:
            paper_dir = Path(directory) / "papers"
            paper_dir.mkdir()
            (paper_dir / "paper-1.json").write_text(json.dumps(bundle))
            context = load_context_index(Path(directory))[bundle["tables"][0]["table_id"]][0]

        prompt_text = _evidence_text(EvidenceItem(
            "table:test", "paper-1", "table_context", "capacity", [], 1.0, "table_seed", [context]
        ))
        self.assertIn("LOCAL_EXTRACTION paper=paper-2", prompt_text)
        self.assertIn("paper-2::evidence_result::0", prompt_text)

    def test_comparison_context_can_seed_retrieval_without_a_claim_match(self) -> None:
        context = {
            "passage_id": "passage:comparison",
            "section": "Results",
            "text": "HSE06 predicts a 2.1 eV gap compared with 1.8 eV in prior work.",
            "match_score": 1.0,
            "evidence_span": "HSE06 predicts a 2.1 eV gap compared with 1.8 eV in prior work.",
            "citations": [],
            "tables": [],
            "context_type": "comparison",
            "paper_id": "paper-1",
            "cross_paper": True,
            "cited_content_status": "requires_resolution",
            "claim_ids": [],
        }

        evidence = retrieve_evidence(
            Task("T1", "Compare HSE06 band gaps", "conflicts"),
            Graph({}, {}),
            context_index={"comparison:test": [context]},
        )

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].retrieval_reason, "comparison_seed")

    def test_unresolved_citation_is_labeled_as_routing_metadata(self) -> None:
        item = EvidenceItem(
            node_id="claim:1",
            paper_id="paper-1",
            role="evidence_result",
            content="A comparison was reported.",
            evidence_spans=[],
            score=1.0,
            retrieval_reason="lexical_role_seed",
            source_contexts=[{
                "passage_id": "passage:1",
                "section": "Results",
                "text": "A comparison was reported [2].",
                "match_score": 1.0,
                "tables": [],
                "citations": [{
                    "mention_text": "[2]",
                    "reference_text": "Smith, Baseline study.",
                    "resolution_status": "metadata_only",
                }],
                "cited_content_status": "requires_resolution",
            }],
        )

        prompt_text = _evidence_text(item)

        self.assertIn("ROUTING_METADATA_ONLY", prompt_text)
        self.assertIn("REQUIRES_RESOLUTION", prompt_text)

    def test_builds_claim_hypothesis_and_source_element_entities(self) -> None:
        record = {
            "paper_id": "paper-1",
            "reconciled_by_role": {
                "hypothesis_statement": [{
                    "content": "A coated interface should improve stability.",
                    "evidence_spans": ["We hypothesize that a coated interface improves stability."],
                }],
            },
        }
        semantic_entities = [{
            "entity_id": "method:test",
            "entity_type": "method",
            "name": "interface coating",
            "description": "coating method",
            "source_paper_id": "paper-1",
            "evidence_span": "coated interface",
            "source_element": "",
            "attributes": {},
            "confidence": 0.9,
        }]
        semantic_relations = [{
            "relation_id": "relation:test",
            "relation_type": "uses_method",
            "source_entity_id": "paper-1::hypothesis_statement::0",
            "target_entity_ids": ["method:test"],
            "source_paper_id": "paper-1",
            "evidence_span": "coated interface",
            "source_element": "",
            "metric": "",
            "subject_value": None,
            "reference_value": None,
            "unit": "",
            "conditions": {},
            "confidence": 0.9,
        }]
        with TemporaryDirectory() as directory:
            record_path = Path(directory) / "paper-1.json"
            source_path = Path(directory) / "paper-1.txt"
            record_path.write_text(json.dumps(record))
            source_path.write_text("Paper title\nFigure 1: Coating cross-section\n")
            with patch("build_evidence_graph._semantic_annotations", return_value=(
                [EvidenceEntity.from_dict(row) for row in semantic_entities],
                [EvidenceRelation.from_dict(row) for row in semantic_relations],
            )):
                bundle = build_paper(record_path, source_path, "Paper title")

        _validate_bundle(bundle)
        entity_types = {row["entity_type"] for row in bundle["entities"]}
        relation_types = {row["relation_type"] for row in bundle["relations"]}
        self.assertTrue({"paper", "atomic_claim", "hypothesis", "figure_table", "method"} <= entity_types)
        self.assertTrue({"derived_from", "uses_method"} <= relation_types)


if __name__ == "__main__":
    unittest.main()