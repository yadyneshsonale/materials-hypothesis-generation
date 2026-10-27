"""Tests for websearch.py (experiment 36, loop.md 17.1): the filters that keep web evidence leak-free."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import websearch as ws
from temporal_hypothesis_benchmark import RetrievalRecord

CASE = "PMC9000001"
OTHER = "PMC9000002"
REGISTRY = {
    CASE: {"paper_id": CASE, "date": "2024-03-01", "split": "test", "doi": "10.1/case", "dois": ["10.1/case"],
           "title": "Oxidation of AlCrNbTiV refractory high entropy alloy at 1000 C", "first_author": "smith"},
    OTHER: {"paper_id": OTHER, "date": "2022-05-01", "split": "test2", "doi": "10.1/other", "dois": ["10.1/other"],
            "title": "Creep of CoCrFeMnNi under tension", "first_author": "lee"},
}
CASES = {CASE: {"paper_id": CASE, "publication_date": "2024-03-01",
                "queries": {"broad": {"text": "How can refractory HEAs resist oxidation?"},
                            "problem_constrained": {"text": "q2"}, "expert_context": {"text": "q3"}}}}
CASE_TEXT = " ".join(f"word{i}" for i in range(400))


def row(**overrides):
    base = {"pmcid": "PMC1", "doi": "10.9/x", "title": "Grain growth in NbMoTaW thin films",
            "authorString": "Jones A, Kim B.", "firstPublicationDate": "2021-01-05",
            "electronicPublicationDate": "2021-01-04", "source": "MED",
            "pubTypeList": {"pubType": ["research-article", "Journal Article"]}, "abstractText": "abc"}
    base.update(overrides)
    return base


def parsed(text: str = "x" * 4000, refs=None):
    return {"title": "T", "abstract": "A", "text": text, "refs": refs or []}


class Registry(unittest.TestCase):
    def setUp(self) -> None:
        self.saved = dict(ws._REGISTRY), dict(ws._SHINGLES)
        ws._REGISTRY.clear()
        ws._REGISTRY.update({"heldout": REGISTRY, "cases": CASES})
        ws._SHINGLES[CASE] = ws.shingles(CASE_TEXT)
        self.flt = ws.CaseFilter(CASE)

    def tearDown(self) -> None:
        ws._REGISTRY.clear()
        ws._REGISTRY.update(self.saved[0])
        ws._SHINGLES.clear()
        ws._SHINGLES.update(self.saved[1])


class CheckRowTests(Registry):
    def test_research_article_before_cutoff_is_kept(self) -> None:
        self.assertIsNone(self.flt.check_row(row()))

    def test_dates_on_or_after_the_cutoff_are_rejected(self) -> None:
        self.assertEqual(self.flt.check_row(row(firstPublicationDate="2024-03-01")), "after_cutoff")
        self.assertEqual(self.flt.check_row(row(electronicPublicationDate="2024-03-02")), "after_cutoff")
        self.assertEqual(self.flt.check_row(row(firstPublicationDate="2024")), "no_date")

    def test_preprints_reviews_and_errata_are_rejected(self) -> None:
        self.assertEqual(self.flt.check_row(row(source="PPR")), "preprint")
        self.assertEqual(self.flt.check_row(row(pubTypeList={"pubType": ["Review"]})), "excluded_type")
        self.assertEqual(self.flt.check_row(row(pubTypeList={"pubType": "Published Erratum"})), "excluded_type")
        self.assertEqual(self.flt.check_row(row(title="Refractory high entropy alloys: a review")),
                         "excluded_type_title")
        self.assertEqual(self.flt.check_row(row(title="Recent progress in high entropy alloys")),
                         "excluded_type_title")

    def test_case_paper_and_its_family_are_rejected(self) -> None:
        self.assertEqual(self.flt.check_row(row(pmcid=CASE)), "case_paper")
        self.assertEqual(self.flt.check_row(row(doi="10.1/CASE")), "case_paper")
        self.assertEqual(self.flt.check_row(row(title="Oxidation of AlCrNbTiV refractory high entropy alloys at 1000 C")),
                         "case_family")
        # Jaccard between 0.5 and 0.8 counts as family only with the same first author.
        similar = "Oxidation of AlCrNbTiV refractory high entropy alloy coatings"
        self.assertIsNone(self.flt.check_row(row(title=similar)))
        self.assertEqual(self.flt.check_row(row(title=similar, authorString="Smith J, Doe A.")), "case_family")

    def test_other_held_out_papers_are_never_evidence(self) -> None:
        self.assertEqual(self.flt.check_row(row(pmcid=OTHER)), "held_out")
        self.assertEqual(self.flt.check_row(row(doi="10.1/other")), "held_out")
        self.assertEqual(self.flt.check_row(row(title="Creep of CoCrFeMnNi under tension")), "held_out")


class CrossrefAndParsedTests(Registry):
    def test_crossref_date_is_required_and_checked(self) -> None:
        self.assertEqual(self.flt.check_crossref(None), "no_crossref_date")
        self.assertEqual(self.flt.check_crossref({"published": None}), "no_crossref_date")
        self.assertEqual(self.flt.check_crossref({"published": "2024-03-01"}), "after_cutoff_crossref")
        self.assertEqual(self.flt.check_crossref({"published": "2020-01-01", "type": "posted-content"}),
                         "excluded_type_crossref")
        self.assertIsNone(self.flt.check_crossref({"published": "2020-01-01", "type": "journal-article"}))

    def test_partial_crossref_dates_count_as_the_end_of_their_period(self) -> None:
        self.assertEqual(ws.end_of_parts([2023]), "2023-12-31")
        self.assertEqual(ws.end_of_parts([2023, 2]), "2023-02-28")
        self.assertEqual(ws.end_of_parts([2024, 2]), "2024-02-29")
        self.assertEqual(ws.end_of_parts([2023, 12]), "2023-12-31")
        self.assertEqual(ws.end_of_parts([2023, 5, 17]), "2023-05-17")
        item = ws._crossref_item({"published": {"date-parts": [[2024, 3]]}, "type": "journal-article", "title": ["T"]})
        self.assertEqual(self.flt.check_crossref(item), "after_cutoff_crossref")  # "March 2024" may be after 1 March
        item = ws._crossref_item({"published": {"date-parts": [[2024, 2]]}, "type": "journal-article", "title": ["T"]})
        self.assertIsNone(self.flt.check_crossref(item))

    def test_papers_citing_the_case_are_rejected(self) -> None:
        self.assertEqual(self.flt.check_parsed(parsed(refs=[{"doi": "10.1/case", "title": ""}])), "cites_case")
        self.assertEqual(self.flt.check_parsed(parsed(refs=[{"doi": "", "title": REGISTRY[CASE]["title"]}])),
                         "cites_case")
        raw = f"Smith J, et al. {REGISTRY[CASE]['title']}. J Alloys Compd. 2024;900:1."
        self.assertEqual(self.flt.check_parsed(parsed(refs=[{"doi": "", "title": "", "raw": raw}])), "cites_case")
        self.assertIsNone(self.flt.check_parsed(parsed(refs=[{"doi": "10.9/y", "title": "Creep of nickel"}])))

    def test_short_texts_and_versions_of_the_case_are_rejected(self) -> None:
        self.assertEqual(self.flt.check_parsed(parsed(text="short")), "short_text")
        self.assertEqual(self.flt.check_parsed(parsed(text="x " * 2000 + CASE_TEXT)), "version_overlap")
        self.assertIsNone(self.flt.check_parsed(parsed(text="x " * 2000 + CASE_TEXT[:150])))


class QueryTests(Registry):
    def test_phrase_query_drops_domain_words_and_filters_dates(self) -> None:
        query = ws.phrase_query("high entropy alloy oxidation resistance", "2024-03-01")
        self.assertIn("ABSTRACT:oxidation OR ABSTRACT:resistance", query)
        self.assertNotIn("ABSTRACT:alloy ", query)
        self.assertIn("FIRST_PDATE:[1900-01-01 TO 2024-02-29]", query)
        self.assertIn("NOT SRC:PPR", query)
        self.assertIn("OPEN_ACCESS:y AND HAS_FT:y", query)

    def test_agent_query_cannot_inject_field_syntax(self) -> None:
        query = ws.agent_query('Cr AND "oxidation" OR NOT FIRST_PDATE:[2025-01-01 TO 2026-01-01]', "2024-03-01")
        free_text, _, rest = query.partition(") AND ")
        self.assertNotIn(":", free_text)
        self.assertNotIn("[", free_text)
        self.assertNotIn(" TO ", free_text)
        self.assertNotIn(" AND ", free_text + " ")
        self.assertEqual(rest, "OPEN_ACCESS:y AND HAS_FT:y AND NOT SRC:PPR AND FIRST_PDATE:[1900-01-01 TO 2024-02-29]")

    def test_bm25_rank_prefers_matching_titles(self) -> None:
        rows = {"PMC1": {"title": "creep of nickel", "abstractText": ""},
                "PMC2": {"title": "oxidation of AlCrNbTiV", "abstractText": "oxidation scale"}}
        self.assertEqual(ws.bm25_rank(["oxidation", "alcrnbtiv"], rows), ["PMC2", "PMC1"])

    def test_corpus_is_per_question(self) -> None:
        self.assertEqual(ws.corpus_stem(CASE, "broad").name, "broad")
        self.assertEqual(ws.corpus_stem(CASE, "broad", CASES[CASE]["queries"]["broad"]["text"]).name, "broad")
        self.assertTrue(ws.corpus_stem(CASE, "broad", "another wording").name.startswith("broad.q"))


ENTRY = {"pmcid": "PMC1", "doi": "10.9/x", "title": "Grain growth", "first_author": "jones", "journal": "J",
         "dates": {"epmc_first": "2021-01-05", "epmc_electronic": "2021-01-04", "crossref": "2021-01-03"},
         "date": "2021-01-03", "latest_date": "2021-01-05", "role": "seed"}
TEXT = ("Grain growth\n\nAbstract\nAbstract text here.\n\nIntroduction\n\n" + "Intro sentence one. " * 100
        + "\nSecond paragraph.\n\n3. Results\n\nResult sentence. " * 3 + "\n\nAuthor Contributions\n\nA did it.\n\n"
        "4. Conclusions\n\nWe conclude that grains grow.")


class RecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parsed = {"title": "Grain growth", "abstract": "Abstract text here.", "text": TEXT}

    def test_sections_follow_headings_and_drop_back_matter(self) -> None:
        sections = ws.sections(self.parsed)
        names = [s for s, _ in sections]
        self.assertEqual(names[0], "Abstract")
        self.assertIn("Introduction", names)
        self.assertIn("4. Conclusions", names)
        self.assertNotIn("Author Contributions", names)
        self.assertFalse(any("A did it." in p for _, p in sections))

    def test_passages_are_verbatim_bounded_and_unique(self) -> None:
        records = ws.passages(ENTRY, self.parsed)
        self.assertTrue(all(len(r.text) <= ws.PASSAGE_CHARS for r in records))
        self.assertEqual(len({r.record_id for r in records}), len(records))
        self.assertTrue(all(r.kind.startswith("web:") and r.structured["source"] == "web" for r in records))
        self.assertTrue(all(r.publication_date == "2021-01-05" for r in records))  # the latest known date
        body = " ".join(p for _, p in ws.sections(self.parsed))
        self.assertTrue(all(piece in body for r in records for piece in r.text.split("  ")))

    def test_card_has_title_abstract_and_conclusions(self) -> None:
        record = ws.card(ENTRY, self.parsed)
        self.assertIn("Abstract: Abstract text here.", record.text)
        self.assertIn("Conclusions: We conclude that grains grow.", record.text)
        self.assertLessEqual(len(record.text), ws.CARD_CHARS)


class AuditTests(Registry):
    def record(self, **structured) -> RetrievalRecord:
        info = {"source": "web", "doi": "10.9/x", "title": "Grain growth",
                "dates": {"epmc_first": "2021-01-05", "epmc_electronic": "", "crossref": "2021-01-03"}}
        info.update(structured)
        return RetrievalRecord("PMC1::web::000::a", structured.pop("paper_id", "PMC1"), "2021-01-05", "web:a", "t",
                               info)

    def test_clean_records_have_zero_counters(self) -> None:
        self.assertEqual(set(ws.audit_records([self.record()], CASE).values()), {0})

    def test_late_held_out_and_case_records_are_counted(self) -> None:
        late = self.record(dates={"epmc_first": "2021-01-05", "crossref": "2024-03-05"})
        undated = self.record(dates={"epmc_first": "2021-01-05", "crossref": ""})
        held = self.record(doi="10.1/other")
        target = self.record(title=REGISTRY[CASE]["title"])
        counts = ws.audit_records([late, undated, held, target], CASE)
        self.assertEqual(counts["temporal_violations"], 2)
        self.assertEqual(counts["family_leaks"], 1)
        self.assertEqual(counts["target_doi_or_title_leaks"], 1)


class CrossrefCacheTests(unittest.TestCase):
    def test_transient_failures_are_retried_and_rejected_dois_are_cached_as_undated(self) -> None:
        def fake(url, params=None):
            if params:
                raise RuntimeError("kept failing")  # the batch request fails
            if "bad" in url:
                raise ValueError("HTTP 400")  # a malformed DOI: permanent
            raise RuntimeError("kept failing")  # transient

        with TemporaryDirectory() as tmp, patch.object(ws, "OUT", Path(tmp)), patch.dict(ws._CROSSREF, clear=True), \
                patch.object(ws, "_crossref_get", fake):
            with self.assertRaises(RuntimeError):
                ws.crossref_works(["10.1/bad", "10.1/good"])
            self.assertIn("10.1/bad", ws._CROSSREF)
            self.assertIsNone(ws._CROSSREF["10.1/bad"])
            self.assertNotIn("10.1/good", ws._CROSSREF)


class WebGraphTests(Registry):
    def test_graph_drops_late_and_held_out_references_and_quotes_citing_sentences(self) -> None:
        papers = [{**ENTRY, "pmcid": "PMC1", "doi": "10.9/a", "title": "Paper A"},
                  {**ENTRY, "pmcid": "PMC2", "doi": "10.9/b", "title": "Paper B", "role": "expansion"}]
        manifest = {"case": CASE, "level": "broad", "seeds": papers[:1], "expansion": papers[1:]}
        refs = [{"rid": "r1", "doi": "10.9/old", "title": "Old work"}, {"rid": "r2", "doi": "10.1/other", "title": ""},
                {"rid": "r3", "doi": "10.9/late", "title": "Late work"}, {"rid": "r4", "doi": "", "title": "No DOI"}]
        sentence = "Earlier work showed that Cr additions refine the oxide scale ⟦r1⟧ and alter creep ⟦r2⟧ ⟦r3⟧."
        parsed = {"title": "T", "abstract": "A", "text": "T\n\nAbstract\nA\n\nBody", "refs": refs,
                  "contexts": [{"rids": ["r1", "r2", "r3"], "sentence": sentence, "previous": ""}]}
        works = {"10.9/old": {"published": "2019-05-01", "type": "journal-article", "title": "Old work"},
                 "10.1/other": {"published": "2021-01-01", "type": "journal-article", "title": "Held"},
                 "10.9/late": {"published": "2024-03-31", "type": "journal-article", "title": "Late work"}}
        with TemporaryDirectory() as tmp, patch.object(ws, "OUT", Path(tmp)), patch.object(ws, "PARSED", Path(tmp)), \
                patch.object(ws, "crossref_works", lambda dois: {d: works.get(d) for d in dois}):
            (Path(tmp) / "corpora" / CASE).mkdir(parents=True)
            (Path(tmp) / "corpora" / CASE / "broad.json").write_text(json.dumps(manifest))
            for pmcid in ("PMC1", "PMC2"):
                (Path(tmp) / f"{pmcid}.json").write_text(json.dumps(parsed))
            graph = ws.web_graph(CASE, level="broad")
        self.assertIn("10.9/old", graph["nodes"])
        self.assertNotIn("10.1/other", graph["nodes"])  # a held-out paper is never a node
        self.assertNotIn("10.9/late", graph["nodes"])  # dated after the cutoff
        old = graph["nodes"]["10.9/old"]
        self.assertEqual(old["pre_cutoff_citations"], 2)  # cited by both corpus papers
        self.assertEqual({s["citer"] for s in old["statements"]}, {"10.9/a", "10.9/b"})
        self.assertTrue(all(s["attributed"].startswith("Earlier work showed") and "⟦" not in s["attributed"]
                            for s in old["statements"]))
        self.assertEqual(graph["nodes"]["10.9/a"]["card"][0].split("\n")[0], "T")


class WebToolsTests(Registry):
    def test_only_listed_papers_can_be_read_and_reads_are_capped(self) -> None:
        with TemporaryDirectory() as tmp:
            papers = Path(tmp)
            for i in range(ws.MAX_READS + 1):
                (papers / f"PMC{i}.json").write_text(json.dumps(
                    {"title": "T", "abstract": "A", "text": "T\n\nAbstract\nA\n\nResults\n\n" + "w " * 3000}))
            with patch.object(ws, "PARSED", papers):
                tools = ws.WebTools(CASE, "broad")
                self.assertIn("error", tools.read_paper(CASE))
                self.assertIn("error", tools.read_paper("PMC0"))
                for i in range(ws.MAX_READS + 1):
                    tools.allowed[f"PMC{i}"] = {**ENTRY, "pmcid": f"PMC{i}"}
                for i in range(ws.MAX_READS):
                    page = tools.read_paper(f"PMC{i}", 1)
                    self.assertLessEqual(len(page["text"]), ws.PAGE_CHARS)
                self.assertEqual(tools.read_paper("PMC0", 1)["record_id"], "PMC0::page::001")  # re-read is free
                self.assertIn("error", tools.read_paper(f"PMC{ws.MAX_READS}", 1))
                self.assertEqual(len(tools.pages), ws.MAX_READS)

    def test_unknown_actions_return_an_error(self) -> None:
        tools = ws.WebTools(CASE, "broad")
        self.assertIn("error", tools.call("delete", {}))
        self.assertIn("error", tools.web_search(""))


if __name__ == "__main__":
    unittest.main()
