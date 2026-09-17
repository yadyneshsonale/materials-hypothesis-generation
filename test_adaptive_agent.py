from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from adaptive_agent import Task, retrieve_evidence, run_workflow
from evidence_model import EvidenceRelation, index_relations, load_relations
from graph_build import Graph, Node


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


class WorkflowRoutingTests(unittest.TestCase):
    def test_user_question_blocks_dependencies_and_synthesis(self) -> None:
        tasks = [
            Task("T1", "Which operating temperature should be used?", "constraints"),
            Task("T2", "Find mechanisms at that temperature.", "mechanisms", ["T1"]),
        ]
        assessment = {
            "decision": "ask_user",
            "finding": "Temperature is required.",
            "cited_ids": [],
            "reason": "The answer changes retrieval.",
            "missing_questions": [],
            "user_question": "What operating temperature should be assumed?",
        }
        with TemporaryDirectory() as directory:
            trace_path = Path(directory) / "trace.json"
            with (
                patch("adaptive_agent.build_graph", return_value=Graph({}, {})),
                patch("adaptive_agent.decompose_goal", return_value=tasks),
                patch("adaptive_agent.retrieve_evidence", return_value=[]),
                patch("adaptive_agent.assess_sufficiency", return_value=assessment),
                patch("adaptive_agent.adjudicate_conflicts", return_value={"conflicts": []}),
                patch("adaptive_agent.synthesize") as synthesize,
            ):
                result = run_workflow("goal", Path(directory), trace_path)

        self.assertEqual(result["status"], "needs_user")
        self.assertEqual(result["tasks"][1]["status"], "blocked_by_user")
        self.assertEqual(result["events"][-1]["stage"], "await_user")
        synthesize.assert_not_called()


if __name__ == "__main__":
    unittest.main()