from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hypothesis_evidence_v2 import (
    HypothesisEvidenceUnit,
    load_evidence,
    write_evidence_record,
)
from materials_extract_v2 import extract_paper


def _row() -> dict:
    return {
        "study_type": "experiment",
        "claim_ownership": "current_paper",
        "sample": {
            "sample_id": "sample_annealed",
            "material_name": "AlCoCrFeNi",
            "nominal_composition": "equiatomic AlCoCrFeNi",
            "composition": [
                {"element": "Al", "fraction": 20.0, "fraction_unit": "at.%"}
            ],
        },
        "process_steps": [{"sequence": 1, "action": "anneal", "parameters": {"temperature": "1000 C"}}],
        "structure_observations": [{"feature": "oxide", "qualitative_value": "dense Cr-rich scale"}],
        "test_conditions": {"temperature": "1000 C", "time": "100 h", "environment": "air"},
        "measurements": [{
            "property": "mass gain",
            "value": 1.2,
            "unit": "mg/cm2",
            "uncertainty": 0.1,
        }],
        "comparison": {"baseline_sample_id": "sample_as_cast", "changed_variables": ["annealing"]},
        "mechanisms": [{
            "assertion": "The dense scale slows oxygen transport.",
            "status": "inferred",
            "evidence_strength": "author_interpretation",
            "source_ownership": "current_paper",
        }],
        "boundaries": [],
        "limitations": [],
        "evidence_spans": ["Mass gain was 1.2 mg/cm2 after 100 h at 1000 C."],
        "extraction_confidence": 0.9,
    }


class HypothesisEvidenceV2Tests(unittest.TestCase):
    def test_accepts_normalized_grounded_unit(self) -> None:
        row = _row()
        unit = HypothesisEvidenceUnit.from_dict(
            row,
            paper_id="paper-1",
            source_text=row["evidence_spans"][0],
        )
        self.assertEqual(unit.measurements[0]["value"], 1.2)
        self.assertEqual(unit.mechanisms[0]["status"], "inferred")

    def test_rejects_text_measurement_value(self) -> None:
        row = _row()
        row["measurements"][0]["value"] = "1.2"
        with self.assertRaisesRegex(ValueError, "must be numeric"):
            HypothesisEvidenceUnit.from_dict(row, paper_id="paper-1")

    def test_accepts_numeric_series_and_structured_limitations(self) -> None:
        row = _row()
        row["measurements"][0]["value"] = [43.57, 50.69, 74.56]
        row["limitations"] = [{
            "type": "measurement",
            "description": "Peak overlap limits phase attribution.",
            "impact": "Minor phases may be missed.",
        }]
        unit = HypothesisEvidenceUnit.from_dict(row, paper_id="paper-1")
        self.assertEqual(len(unit.measurements[0]["value"]), 3)
        self.assertEqual(unit.limitations[0]["type"], "measurement")

    def test_rejects_unknown_mechanism_status(self) -> None:
        row = _row()
        row["mechanisms"][0]["status"] = "proven"
        with self.assertRaisesRegex(ValueError, "status must be one of"):
            HypothesisEvidenceUnit.from_dict(row, paper_id="paper-1")

    def test_round_trip(self) -> None:
        unit = HypothesisEvidenceUnit.from_dict(_row(), paper_id="paper-1")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "paper-1.json"
            write_evidence_record(path, "paper-1", [unit], chunks_processed=1)
            loaded = load_evidence(path)
            payload = json.loads(path.read_text())
        self.assertEqual(loaded, [unit])
        self.assertEqual(payload["schema_version"], "hypothesis-evidence-2.0")

    @patch("materials_extract_v2.chat_json", return_value={"units": []})
    def test_extractor_resumes_completed_chunks(self, chat_mock) -> None:
        source = "Introduction\nPrior work is limited.\nMethods\nThe alloy was annealed."
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "paper-1.txt"
            checkpoint_dir = root / "checkpoints"
            source_path.write_text(source)
            first = extract_paper(source_path, checkpoint_dir)
            second = extract_paper(source_path, checkpoint_dir)
        self.assertGreater(first.model_calls, 0)
        self.assertEqual(second.model_calls, 0)
        self.assertEqual(second.resumed_chunks, second.chunks_processed)
        self.assertEqual(chat_mock.call_count, first.model_calls)


if __name__ == "__main__":
    unittest.main()
