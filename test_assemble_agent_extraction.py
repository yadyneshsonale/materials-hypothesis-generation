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

    def test_reconciles_agent_grouped_claims(self) -> None:
        claims = [{
            "role": "problem_motivation",
            "content": "General gap.",
            "evidence_span": "Strength remains difficult.",
            "reconcile_group": "strength-gap",
            "reconciled_content": "High strength with ductility remains difficult.",
        }, {
            "role": "problem_motivation",
            "content": "Quantified gap.",
            "evidence_span": "The target is 2 GPa and 10% ductility.",
            "reconcile_group": "strength-gap",
            "reconciled_content": "High strength with ductility remains difficult.",
        }]

        record = assemble(
            "paper", "Strength remains difficult. The target is 2 GPa and 10% ductility.", claims
        )

        self.assertEqual(len(record["raw_by_role"]["problem_motivation"]), 2)
        self.assertEqual(len(record["reconciled_by_role"]["problem_motivation"]), 1)
        self.assertEqual(len(record["reconciled_by_role"]["problem_motivation"][0]["evidence_spans"]), 2)


if __name__ == "__main__":
    unittest.main()