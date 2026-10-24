from __future__ import annotations

import unittest
from unittest.mock import patch

import citegraph as cg

JATS = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><front><article-meta><title-group>
<article-title>Laves phase in HfMoTaTiZr</article-title></title-group><abstract><p>Abstract text.</p></abstract>
</article-meta></front><body><sec><title>Introduction</title>
<p>Cr additions form Laves phases [<xref ref-type="bibr" rid="B1">1</xref>]. Earlier work disagreed
[<xref ref-type="bibr" rid="B2">2</xref>&#8211;<xref ref-type="bibr" rid="B4">4</xref>]. No citation here.</p>
<p>Wide cluster [<xref ref-type="bibr" rid="B1">1</xref>,<xref ref-type="bibr" rid="B2">2</xref>,
<xref ref-type="bibr" rid="B3">3</xref>,<xref ref-type="bibr" rid="B4">4</xref>,<xref ref-type="bibr" rid="B5">5</xref>].</p>
<sec sec-type="ref-list"><ref-list>
<ref id="B1"><mixed-citation>A. Author. Laves phases. 2019. <ext-link ext-link-type="doi" xlink:href="10.1/ABC"/></mixed-citation></ref>
<ref id="B2"><mixed-citation><article-title>Second work</article-title> doi: 10.1016/j.xyz.2020.01.</mixed-citation></ref>
<ref id="B3"><mixed-citation><pub-id pub-id-type="pmid">123</pub-id></mixed-citation></ref>
<ref id="B4"><mixed-citation>Fourth.</mixed-citation></ref>
<ref id="B5"><mixed-citation>Fifth.</mixed-citation></ref>
</ref-list></sec></sec></body></article>"""


def _node(wid: str, statements: list[dict] | None = None, card: list[str] | None = None, date: str = "2020-01-01",
          citations: int = 5) -> dict:
    statements = statements or []
    return {"id": wid, "pmcid": "PMC1" if card else "", "title": f"Title {wid}", "doi": f"10.9/{wid}",
            "publication_date": date, "pre_cutoff_citations": citations, "roles": [], "card": card or [],
            "statements": statements, "references": [], "citers": sorted({s["citer"] for s in statements})}


def _statement(citer: str, relation: str = "finding", text: str = "Cr forms Laves phase") -> dict:
    return {"ctx": "c0", "rid": "B1", "cited": "W1", "relation": relation, "attributed": text,
            "cited_system": "HfMoTaTiZr", "applied_to": "not stated", "numbers": "", "quote": text,
            "grounding": 1.0, "citer": citer, "citer_title": f"Citer {citer}", "citer_date": "2021-05-01"}


class CitationCountTests(unittest.TestCase):
    def test_pre_cutoff_citations_removes_cutoff_year_and_later(self) -> None:
        work = {"cited_by_count": 100, "counts_by_year": [{"year": 2025, "cited_by_count": 30},
                                                          {"year": 2024, "cited_by_count": 20},
                                                          {"year": 2023, "cited_by_count": 15}]}
        self.assertEqual(cg.pre_cutoff_citations(work, "2024-01-02"), 50)

    def test_day_before(self) -> None:
        self.assertEqual(cg.day_before("2024-01-01"), "2023-12-31")


class ExclusionTests(unittest.TestCase):
    def test_target_is_excluded_by_doi_pmcid_and_near_duplicate_title(self) -> None:
        exclusion = {"dois": {"10.1/target"}, "pmcids": {"PMCT"},
                     "titles": [cg.title_tokens("Reticulated Laves network toughens HfMoTaTiZr refractory alloy")]}
        self.assertTrue(cg.is_excluded(exclusion, doi="https://doi.org/10.1/TARGET"))
        self.assertTrue(cg.is_excluded(exclusion, pmcid="PMCT"))
        self.assertTrue(cg.is_excluded(exclusion, title="Reticulated Laves network toughens HfMoTaTiZr refractory alloys"))
        self.assertFalse(cg.is_excluded(exclusion, doi="10.1/other", title="Oxidation of NbMoTaW"))


class ParseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parsed = cg.parse_jats("PMCX", JATS)

    def test_references_inside_body_are_found_with_ids(self) -> None:
        refs = {r["rid"]: r for r in self.parsed["refs"]}
        self.assertEqual(len(refs), 5)
        self.assertEqual(refs["B1"]["doi"], "10.1/abc")
        self.assertEqual(refs["B2"]["doi"], "10.1016/j.xyz.2020.01")
        self.assertEqual(refs["B3"]["pmid"], "123")

    def test_citation_ranges_expand_and_uncited_sentences_are_skipped(self) -> None:
        contexts = self.parsed["contexts"]
        self.assertEqual(contexts[0]["rids"], ["B1"])
        self.assertEqual(contexts[1]["rids"], ["B2", "B3", "B4"])
        self.assertEqual(len(contexts[2]["rids"]), 5)
        self.assertEqual(len(contexts), 3)

    def test_reference_list_is_not_body_text(self) -> None:
        self.assertNotIn("Fourth.", self.parsed["text"])
        self.assertIn("Cr additions form Laves phases", self.parsed["text"])

    def test_wide_clusters_are_not_used(self) -> None:
        parsed = {**self.parsed, "resolved": {"B1": "W1", "B2": "W2", "B3": "W3"}}
        used = cg.usable_contexts(parsed)
        self.assertTrue(all(len(c["rids"]) <= cg.MAX_REFS_PER_CONTEXT for c in used))
        self.assertEqual(len(used), 2)

    def test_marker_rendering(self) -> None:
        sentence = self.parsed["contexts"][1]["sentence"]
        rendered = cg.marker_text(sentence, {"B2": "R1", "B3": "R2", "B4": "R3"})
        self.assertIn("[R1]", rendered)
        self.assertNotIn("⟦", rendered)
        self.assertNotIn("⟦", cg.clean_sentence(sentence))


class ExtractionValidationTests(unittest.TestCase):
    def test_grounding_rejects_invented_claims(self) -> None:
        source = "Cr additions form Laves phases in HfMoTaTiZr at 1200 C"
        self.assertGreaterEqual(cg.grounding("Cr forms Laves phases in HfMoTaTiZr", source), cg.MIN_GROUNDING)
        self.assertLess(cg.grounding("Oxidation resistance improved by aluminium scale", source), cg.MIN_GROUNDING)


class ProfileTests(unittest.TestCase):
    def test_profile_contains_card_and_citer_statements_with_contradictions_first(self) -> None:
        node = _node("W1", [_statement("W8", "finding"), _statement("W9", "contradicts", "Laves not observed")],
                     card=["Paper card. System: HfMoTaTiZr."])
        text = cg.profile_text(node, corroboration=True)
        self.assertIn("Own digest", text)
        self.assertIn("Corroboration: 2 independent citing papers", text)
        self.assertLess(text.index("contradicts"), text.index("- finding"))

    def test_record_date_is_latest_of_node_and_citers(self) -> None:
        node = _node("W1", [_statement("W8")], date="2019-01-01")
        self.assertEqual(cg.node_date(node, "2024-01-01"), "2021-05-01")

    def test_corroboration_breaks_relevance_ties_by_independent_citers(self) -> None:
        graph = {"cutoff": "2024-01-01"}
        few = cg.node_record(_node("W1", [_statement("W8")]), graph, "Laves phase Cr HfMoTaTiZr ductility")
        many = cg.node_record(_node("W2", [_statement(f"W{i}") for i in range(10, 15)]), graph,
                              "Laves phase Cr HfMoTaTiZr ductility")
        ranked = cg.corroboration_rank("Cr Laves phase ductility", [few, many])
        self.assertEqual(ranked[0].record_id, "node::W2")

    def test_pack_respects_shared_budget(self) -> None:
        graph = {"cutoff": "2024-01-01"}
        records = [cg.node_record(_node(f"W{i}"), graph, "x" * 3000) for i in range(10)]
        packed = cg.pack_ranked(records, cg.PROFILE_CAP)
        self.assertLessEqual(sum(min(len(r.text), cg.PROFILE_CAP) for r in packed), cg.rx.EVIDENCE_BUDGET_CHARS)


class GraphAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        nodes = {"W1": _node("W1", [_statement("W2")], card=["Paper card. Cr Laves HfMoTaTiZr."]),
                 "W2": _node("W2", card=["Paper card. NbMoTaW oxidation."])}
        nodes["W2"]["references"] = ["W1"]
        self.graph = {"cutoff": "2024-01-01", "nodes": nodes, "edges": [("W2", "W1")]}

    def test_tools_navigate_graph(self) -> None:
        tools = cg.GraphTools(self.graph)
        self.assertEqual(tools.who_cites("node::W1")["statements"][0]["citer"], "node::W2")
        self.assertEqual(tools.references("node::W2")["references"][0]["node_id"], "node::W1")
        self.assertEqual(len(tools.path("node::W1", "node::W2")["path"]), 2)

    def test_citing_unread_node_is_rejected_then_accepted_after_reading(self) -> None:
        hypothesis = {"hypothesis": "Add Cr", "supporting_evidence_ids": ["node::W1"], "conflicting_evidence_ids": []}
        script = [
            {"tool_calls": [{"id": "1", "function": {"name": "submit_hypothesis",
                                                     "arguments": cg.json.dumps({"hypothesis": hypothesis})}}]},
            {"tool_calls": [{"id": "2", "function": {"name": "read_node", "arguments": '{"node_id": "node::W1"}'}}]},
            {"tool_calls": [{"id": "3", "function": {"name": "submit_hypothesis",
                                                     "arguments": cg.json.dumps({"hypothesis": hypothesis})}}]},
        ]
        calls = iter(script)
        tools = cg.GraphTools(self.graph)
        result = cg.run_graph_agent("Cr in HfMoTaTiZr", "2024-01-01", tools, call_model=lambda m, t: next(calls))
        self.assertEqual(result["generation"]["supporting_evidence_ids"], ["node::W1"])
        self.assertFalse(result["trace"][0]["accepted"])
        self.assertEqual(result["tool_calls"], 1)


class LeakageTests(unittest.TestCase):
    def test_graph_leakage_flags_target_doi(self) -> None:
        case = {"paper_id": "PMCT", "publication_date": "2024-01-02"}
        record = cg.RetrievalRecord("node::W1", "W1", "2020-01-01", "graph_node", "t", {"doi": "10.1/target"})
        exclusion = {"dois": {"10.1/target"}, "pmcids": {"PMCT"}, "titles": []}
        with patch.object(cg, "target_exclusion", return_value=exclusion), \
                patch.object(cg.rx, "leakage_audit", return_value={"temporal_violations": 0}):
            self.assertEqual(cg.graph_leakage([record], case)["target_doi_or_title_leaks"], 1)


if __name__ == "__main__":
    unittest.main()
