from __future__ import annotations

import unittest
from collections import Counter

import extractor_leakage_audit as xa

CASE = {
    "hidden_target": {"material_initial_state": "As-cast HfMoTaTiZr", "conditions": "room temperature compression",
                      "baseline": "HfMoTaTiZr", "intervention": "Addition of Cr by arc melting",
                      "structural_mediator": "reticulated Laves phase network",
                      "mechanism": "crack deflection by the Laves network", "predicted_outcome": "higher strength"},
    "queries": {"broad": {"text": "Improve refractory alloys."}, "problem_constrained": {"text": "Reduce density."},
                "expert_context": {"text": "Earlier work used arc melting."}},
}


class StemTests(unittest.TestCase):
    def test_inflections_share_a_stem(self) -> None:
        self.assertEqual(xa.stem("pinning"), xa.stem("pinned"))
        self.assertEqual(xa.stem("reticulated"), xa.stem("reticulation"))
        self.assertEqual(xa.stem("reticulate"), xa.stem("reticulation"))
        self.assertEqual(xa.stem("stabilized"), xa.stem("stabilization"))
        self.assertEqual(xa.stem("stabilize"), xa.stem("stabilization"))
        self.assertEqual(xa.stem("sintered"), xa.stem("sintering"))
        self.assertEqual(xa.stem("precipitating"), xa.stem("precipitation"))
        self.assertEqual(xa.stem("laves"), xa.stem("laves"))
        self.assertIn("cr", xa.stems("Addition of Cr"))
        self.assertNotIn("the", xa.stems("the network"))


class LabelTests(unittest.TestCase):
    def test_rubric_labels_are_not_content(self) -> None:
        text = xa.strip_labels("Gap and lever. Type: limitation. Statement: brittle. Lever: Cr content.")
        self.assertNotIn("gap", xa.stems(text))
        self.assertIn("brittle", xa.stems(text))


class VocabularyTests(unittest.TestCase):
    def test_answer_vocabulary_excludes_context_query_and_common_words(self) -> None:
        doc_freq = Counter({"network": 40, "lave": 1})
        vocab = xa.answer_vocabulary(CASE, doc_freq, 50)
        self.assertIn(xa.stem("laves"), vocab)
        self.assertIn("cr", vocab)
        self.assertNotIn("network", vocab)          # in more than 20% of corpus papers
        self.assertNotIn(xa.stem("melting"), vocab)  # stated in the query
        self.assertNotIn("hfmotatizr", vocab)        # starting material is allowed context


if __name__ == "__main__":
    unittest.main()
