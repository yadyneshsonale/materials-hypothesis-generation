from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from adaptive_agent import (
    EvidenceItem,
    Task,
    decompose_goal,
    retrieve_materials_evidence,
    select_synthesis_evidence,
)
from materials_evidence import MaterialsEvidenceUnit, load_materials_evidence, write_materials_record


def _valid_row() -> dict:
    return {
        "evidence_type": "experiment",
        "material": {"name": "AlCoCrFeNi", "composition": "equiatomic"},
        "intervention": {"action": "oxidize", "description": "Expose at 1000 C"},
        "structure": {"description": "Cr-rich protective oxide"},
        "mechanism": "The dense oxide slows oxygen transport.",
        "outcome": {"property": "mass gain", "value": 1.2, "unit": "mg/cm2"},
        "conditions": {"temperature": "1000 C", "time": "100 h", "environment": "air"},
        "comparison": {"baseline_material": "unalloyed substrate", "direction": "lower"},
        "evidence_spans": ["Mass gain was 1.2 mg/cm2 after 100 h at 1000 C."],
        "confidence": 0.9,
    }


class MaterialsEvidenceTests(unittest.TestCase):
    def test_accepts_linked_grounded_unit(self) -> None:
        row = _valid_row()
        unit = MaterialsEvidenceUnit.from_dict(
            row,
            paper_id="paper-1",
            source_text=row["evidence_spans"][0],
        )

        self.assertIn("mechanism", unit.facets())
        self.assertIn("conditions", unit.facets())
        self.assertTrue(unit.unit_id.startswith("paper-1::materials_evidence::"))

    def test_rejects_disconnected_material_fact(self) -> None:
        row = _valid_row()
        row["intervention"] = {}
        row["structure"] = {}

        with self.assertRaisesRegex(ValueError, "must link"):
            MaterialsEvidenceUnit.from_dict(row, paper_id="paper-1")

    def test_empty_nested_fields_do_not_count_as_facets(self) -> None:
        row = _valid_row()
        row["structure"] = {"description": "", "phases": [], "defects": []}
        row["conditions"] = {"temperature": "null", "environment": ""}
        row["comparison"] = {"baseline_material": "", "baseline_value": None}
        unit = MaterialsEvidenceUnit.from_dict(row, paper_id="paper-1")

        self.assertNotIn("structure", unit.facets())
        self.assertNotIn("conditions", unit.facets())
        self.assertNotIn("comparison", unit.facets())

    def test_rejects_placeholder_only_link(self) -> None:
        row = _valid_row()
        row["intervention"] = {"action": "not explicitly stated"}
        row["structure"] = {"description": "", "phases": []}

        with self.assertRaisesRegex(ValueError, "must link"):
            MaterialsEvidenceUnit.from_dict(row, paper_id="paper-1")

    def test_rejects_non_verbatim_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-verbatim"):
            MaterialsEvidenceUnit.from_dict(
                _valid_row(),
                paper_id="paper-1",
                source_text="Different source text.",
            )

    def test_round_trip_record(self) -> None:
        unit = MaterialsEvidenceUnit.from_dict(_valid_row(), paper_id="paper-1")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "paper-1.json"
            write_materials_record(path, "paper-1", [unit])
            loaded = load_materials_evidence(Path(directory))
            schema_version = json.loads(path.read_text())["schema_version"]

        self.assertEqual(loaded, [unit])
        self.assertEqual(schema_version, "1.0")

    def test_retrieval_rewards_complete_linked_chain(self) -> None:
        unit = MaterialsEvidenceUnit.from_dict(_valid_row(), paper_id="paper-1")
        task = Task(
            "T1",
            "Which oxidation mechanism lowers mass gain at 1000 C?",
            "causal_chain",
            required_facets=["material", "structure", "mechanism", "outcome", "conditions"],
        )

        evidence = retrieve_materials_evidence(task, [unit])

        self.assertEqual([item.node_id for item in evidence], [unit.unit_id])
        self.assertEqual(evidence[0].retrieval_reason, "linked_materials_evidence")
        self.assertEqual(evidence[0].structured_context["conditions"]["temperature"], "1000 C")

    def test_planner_questions_have_explicit_decision_value(self) -> None:
        tasks = decompose_goal("increase creep strength of refractory HEAs above 1000 C")

        self.assertEqual([task.intent for task in tasks], [
            "baseline", "causal_chain", "intervention", "boundary", "discrimination",
        ])
        self.assertTrue(all(task.decision_use for task in tasks))
        self.assertTrue(all(task.required_facets for task in tasks))
        self.assertEqual(tasks[-1].depends_on, ["T3", "T4"])

    def test_synthesis_evidence_prioritizes_citations_and_respects_limit(self) -> None:
        evidence = [
            EvidenceItem(f"node-{index}", f"paper-{index}", "materials_evidence_unit", "", [], index, "test")
            for index in range(4)
        ]
        task = Task("T1", "question", "baseline", cited_ids=["node-1", "node-0"])

        selected = select_synthesis_evidence([task], evidence, limit=3)

        self.assertEqual([item.node_id for item in selected], ["node-1", "node-0", "node-3"])


if __name__ == "__main__":
    unittest.main()
