from __future__ import annotations

import json
import unittest

import llm_client as lc
import query_builder_v3 as qb

TARGET = {"material_initial_state": "As-cast HfMoTaTiZr single-phase BCC", "conditions": "room temperature compression",
          "baseline": "HfMoTaTiZr", "intervention": "Addition of 4.2 at.% Cr by arc melting",
          "structural_mediator": "reticulated Laves phase network",
          "mechanism": "solid solution hardening and crack deflection by the Laves network"}


class RedactionTests(unittest.TestCase):
    def test_self_reference_patterns(self) -> None:
        for sentence in ("In this study, two RHEAs were prepared by arc melting.",
                         "Here, we demonstrate that HPHT treatment transforms lamellae.",
                         "Herein, Cr was added.", "This study aimed to analyze the wear mechanism.",
                         "We propose a machine-learning potential.", "The aim of this work was to add Cr."):
            self.assertTrue(qb.SELF_REFERENCE.search(sentence), sentence)
        for sentence in ("Earlier work added Al to improve oxidation resistance.",
                         "MoNbTaW retains strength up to 1600 °C but is brittle."):
            self.assertIsNone(qb.SELF_REFERENCE.search(sentence), sentence)

    def test_citation_markers_removed(self) -> None:
        self.assertEqual(qb._strip_citations("strength [1, 2] and ductility [3–5]."), "strength and ductility.")


class GateTests(unittest.TestCase):
    def test_starting_material_words_are_allowed(self) -> None:
        overlap, shared = qb.answer_overlap("Improve the ductility of as-cast HfMoTaTiZr at room temperature.", TARGET)
        self.assertEqual(overlap, 0.0)
        self.assertEqual(shared, [])

    def test_solution_words_count(self) -> None:
        overlap, shared = qb.answer_overlap("Add Cr to form a reticulated Laves network.", TARGET)
        self.assertGreater(overlap, qb.MAX_OVERLAP)
        self.assertIn("laves", shared)

    def test_revision_requests_list_phrases_not_target(self) -> None:
        results = {"broad": {"passed": True, "leaks": [], "steers_to_answer": False, "overlap": 0.0, "shared_words": []},
                   "expert_context": {"passed": False, "leaks": [{"phrase": "secondary intermetallic",
                                                                  "reveals": "structural_mediator"}],
                                      "steers_to_answer": True, "overlap": 0.2, "shared_words": ["laves"]}}
        requests_ = qb.revision_requests(results)
        self.assertEqual(list(requests_), ["expert_context"])
        text = json.dumps(requests_)
        self.assertIn("secondary intermetallic", text)
        self.assertNotIn("4.2 at.%", text)


class SingleToolAdapterTests(unittest.TestCase):
    TOOLS = [{"type": "function", "function": {"name": "search_corpus", "description": "Search.",
                                               "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}}},
             {"type": "function", "function": {"name": "submit_hypothesis", "description": "Submit.",
                                               "parameters": {"type": "object", "properties": {"hypothesis": {"type": "object"}}}}}]

    def test_wrap_lists_every_tool(self) -> None:
        wrapped = lc.wrap_tools(self.TOOLS)
        self.assertEqual(len(wrapped), 1)
        fn = wrapped[0]["function"]
        self.assertEqual(fn["parameters"]["properties"]["tool"]["enum"], ["search_corpus", "submit_hypothesis"])
        self.assertIn("search_corpus", fn["description"])

    def test_round_trip(self) -> None:
        native = {"role": "assistant", "content": "", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "search_corpus", "arguments": '{"query": "Laves"}'}}]}
        wrapped = lc._wrap_message(native)
        self.assertEqual(wrapped["tool_calls"][0]["function"]["name"], lc.SINGLE_TOOL_NAME)
        back = lc._unwrap_message(wrapped)
        self.assertEqual(back["tool_calls"][0]["function"]["name"], "search_corpus")
        self.assertEqual(json.loads(back["tool_calls"][0]["function"]["arguments"]), {"query": "Laves"})

    def test_unwrap_accepts_string_arguments(self) -> None:
        message = {"role": "assistant", "tool_calls": [{"id": "x", "function": {"name": "act", "arguments": json.dumps(
            {"tool": "submit_hypothesis", "arguments": json.dumps({"hypothesis": {"hypothesis": "h"}})})}}]}
        back = lc._unwrap_message(message)
        self.assertEqual(json.loads(back["tool_calls"][0]["function"]["arguments"])["hypothesis"]["hypothesis"], "h")


if __name__ == "__main__":
    unittest.main()
