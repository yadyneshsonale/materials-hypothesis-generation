from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from package_pipeline_outputs import package_pipeline, validate_pipeline


class PackagePipelineOutputsTests(unittest.TestCase):
    def test_packages_and_validates_numbered_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = []
            for rank in range(1, 51):
                paper_id = f"PMC{rank}"
                manifest.append({
                    "rank": rank,
                    "paper_id": paper_id,
                    "title": f"Paper {rank}",
                })
                assets = root / "outputs" / "papers" / paper_id / "input"
                assets.mkdir(parents=True)
                (assets / "article.pdf").write_bytes(b"%PDF-test")
                (assets / "article.xml").write_text("<article/>")
                questions = root / "question_centered" / "resolved_questions"
                questions.mkdir(parents=True, exist_ok=True)
                (questions / f"{paper_id}.json").write_text(json.dumps({
                    "paper_id": paper_id,
                    "questions": [{"question": "Why?"}],
                }))
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest))

            index = package_pipeline(
                root,
                manifest_path,
                "question_centered",
            )
            result = validate_pipeline(
                root,
                manifest_path,
                "question_centered",
            )

            self.assertEqual(index["paper_count"], 50)
            self.assertEqual(result["question_count"], 50)
            self.assertTrue(result["verified"])
            self.assertEqual(
                json.loads(
                    (root / "question_centered" / "outputs" / "1" / "metadata.json")
                    .read_text()
                )["paper_id"],
                "PMC1",
            )


if __name__ == "__main__":
    unittest.main()
