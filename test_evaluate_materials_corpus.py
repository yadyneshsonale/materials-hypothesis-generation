from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from evaluate_materials_corpus import evaluate
from materials_evidence import MaterialsEvidenceUnit, write_materials_record
from test_materials_evidence import _valid_row


class EvaluateMaterialsCorpusTests(unittest.TestCase):
    def test_reports_grounded_complete_units_and_missing_outputs(self) -> None:
        row = _valid_row()
        unit = MaterialsEvidenceUnit.from_dict(row, paper_id="paper-1")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_dir = root / "source"
            evidence_dir = root / "evidence"
            source_dir.mkdir()
            (source_dir / "paper-1.txt").write_text(row["evidence_spans"][0])
            (source_dir / "paper-2.txt").write_text("No output yet.")
            write_materials_record(evidence_dir / "paper-1.json", "paper-1", [unit])

            result = evaluate(evidence_dir, source_dir)

        self.assertEqual(result["valid_units"], 1)
        self.assertEqual(result["verbatim_grounding_rate"], 1.0)
        self.assertEqual(result["complete_core_chain_rate"], 1.0)
        self.assertEqual(result["missing_output_papers"], ["paper-2"])
        self.assertEqual(result["invalid_unit_count"], 0)

    def test_reports_invalid_non_verbatim_unit(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_dir = root / "source"
            evidence_dir = root / "evidence"
            source_dir.mkdir()
            evidence_dir.mkdir()
            (source_dir / "paper-1.txt").write_text("Different source.")
            (evidence_dir / "paper-1.json").write_text(json.dumps({
                "paper_id": "paper-1",
                "evidence_units": [_valid_row()],
                "rejected_units": [],
            }))

            result = evaluate(evidence_dir, source_dir)

        self.assertEqual(result["valid_units"], 0)
        self.assertEqual(result["invalid_unit_count"], 1)


if __name__ == "__main__":
    unittest.main()
