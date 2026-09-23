from __future__ import annotations

import unittest

from apply_agent_review import apply_review


class ApplyAgentReviewTests(unittest.TestCase):
    def test_applies_remove_update_and_add(self) -> None:
        payload = {"paper_id": "paper", "claims": [
            {"role": "constraint", "content": "old", "evidence_span": "keep"},
            {"role": "causal_claim", "content": "remove", "evidence_span": "drop"},
        ]}
        review = {
            "paper_id": "paper",
            "remove_evidence_spans": ["drop"],
            "update": [{"evidence_span": "keep", "role": "evidence_result", "content": "new"}],
            "add": [{"role": "prior_approach", "content": "added", "evidence_span": "source"}],
        }

        updated = apply_review(payload, review)

        self.assertEqual(updated["claims"], [
            {"role": "evidence_result", "content": "new", "evidence_span": "keep"},
            {"role": "prior_approach", "content": "added", "evidence_span": "source"},
        ])


if __name__ == "__main__":
    unittest.main()