from __future__ import annotations

import unittest

from assemble_agent_extraction import assemble
from roles import ROLE_KEYS


class AssembleAgentExtractionTests(unittest.TestCase):
    def test_builds_complete_role_schema_from_verbatim_claims(self) -> None:
        record = assemble("paper", "Abstract\n\nMeasured strength increased.", [{
            "role": "evidence_result",
            "content": "Strength increased.",
            "evidence_span": "Measured strength increased.",
        }])

        self.assertEqual(set(record["raw_by_role"]), set(ROLE_KEYS))
        self.assertEqual(set(record["reconciled_by_role"]), set(ROLE_KEYS))
        self.assertEqual(record["chunks_processed"], 1)

    def test_rejects_non_verbatim_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-verbatim evidence"):
            assemble("paper", "source", [{
                "role": "evidence_result", "content": "claim", "evidence_span": "missing"
            }])


if __name__ == "__main__":
    unittest.main()