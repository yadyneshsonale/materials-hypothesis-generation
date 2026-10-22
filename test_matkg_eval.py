from __future__ import annotations

import csv
import io
import json
import sqlite3
import tarfile
import tempfile
import unittest
from pathlib import Path

from matkg_index import TemporalKG, build_index, candidate_phrases
from temporal_eval_v3 import EligibleCorpus, audit_accessed, kg_excluded_dois, run_tool_agent
from temporal_hypothesis_benchmark import RetrievalRecord

HEADER = ["Unnamed: 0", "Entity", "Part_of_text", "NER_Tag", "DOI", "Preferred_Entity", "Year"]
ROWS = [
    # doi A (2019): an earlier paper on the query terms
    ["0", "high entropy alloy", "Abs", "CHM", "10.1/a", "High Entropy Alloy", "2019.0"],
    ["1", "hf", "Abs", "CHM", "10.1/a", "Hf", "2019.0"],
    ["2", "ductility", "Abs", "PRO", "10.1/a", "Ductility", "2019.0"],
    ["3", "nb", "Abs", "CHM", "10.1/a", "Nb", "2019.0"],
    # doi B (2020): shares Hf and Nb
    ["4", "hf", "Abs", "CHM", "10.1/b", "Hf", "2020.0"],
    ["5", "nb", "Abs", "CHM", "10.1/b", "Nb", "2020.0"],
    ["6", "hardness", "Abs", "PRO", "10.1/b", "Hardness", "2020.0"],
    # doi C (2023): after the cutoff year, must never contribute
    ["7", "hf", "Abs", "CHM", "10.1/c", "Hf", "2023.0"],
    ["8", "nb", "Abs", "CHM", "10.1/c", "Nb", "2023.0"],
    ["9", "creep", "Abs", "PRO", "10.1/c", "Creep", "2023.0"],
    # doi T: the held-out paper, must be excluded
    ["10", "hf", "Abs", "CHM", "10.1/t", "Hf", "2020.0"],
    ["11", "zirconium", "Abs", "CHM", "10.1/t", "Zirconium", "2020.0"],
    # bad year is skipped, not guessed
    ["12", "hf", "Abs", "CHM", "10.1/d", "Hf", ""],
]


def _write_archive(path: Path) -> None:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(HEADER)
    writer.writerows(ROWS)
    payload = buffer.getvalue().encode("utf-8")
    with tarfile.open(path, "w:gz") as tar:
        info = tarfile.TarInfo("ENTDOI.csv")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))


class MatKGTests(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        root = Path(self._dir.name)
        self.archive = root / "ENTDOI.csv.tar.gz"
        self.db = root / "index" / "entdoi.sqlite"
        _write_archive(self.archive)
        self.stats = build_index(self.archive, self.db)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_index_skips_rows_without_a_usable_year(self) -> None:
        self.assertEqual(self.stats["rows_read"], len(ROWS))
        self.assertEqual(self.stats["rows_skipped"], 1)
        self.assertEqual(self.stats["year_max"], 2023)

    def test_candidate_phrases_cover_multiword_terms(self) -> None:
        phrases = candidate_phrases("High entropy alloy ductility")
        self.assertIn("high entropy alloy", phrases)
        self.assertIn("ductility", phrases)

    def test_lookup_uses_only_pre_cutoff_non_excluded_papers(self) -> None:
        kg = TemporalKG(self.db, "2021-03-01", {"10.1/t"})
        try:
            found = kg.cooccurrences("Hf ductility")
        finally:
            kg.close()
        neighbors = {fact["neighbor"] for fact in found["facts"]}
        self.assertIn("nb", neighbors)
        self.assertNotIn("zirconium", neighbors)
        self.assertNotIn("creep", neighbors)
        for fact in found["facts"]:
            self.assertLess(fact["latest_year"], 2021)
            self.assertGreater(fact["association"], 0)

    def test_association_ranks_specific_neighbors_first(self) -> None:
        kg = TemporalKG(self.db, "2021-03-01", set())
        try:
            found = kg.cooccurrences("Hf ductility")
        finally:
            kg.close()
        self.assertEqual(found["facts"][0]["neighbor"], "nb")
        self.assertEqual(found["facts"][0]["papers"], 2)

    def test_excluded_target_dois_are_removed_even_if_they_match(self) -> None:
        kg = TemporalKG(self.db, "2021-03-01", {"10.1/a"})
        try:
            found = kg.cooccurrences("Hf ductility")
        finally:
            kg.close()
        self.assertNotIn("high entropy alloy", {fact["neighbor"] for fact in found["facts"]})

    def test_kg_excluded_dois_covers_target_and_family(self) -> None:
        metadata = {
            "T": {"doi": "10.1/t", "work_family_id": "fam-1"},
            "P": {"doi": "10.1/preprint", "work_family_id": "fam-1"},
            "O": {"doi": "10.1/other", "work_family_id": "fam-2"},
        }
        self.assertEqual(kg_excluded_dois("T", metadata), {"10.1/t", "10.1/preprint"})

    def test_kg_lookup_facts_are_readable_records_before_cutoff(self) -> None:
        kg = TemporalKG(self.db, "2021-03-01", {"10.1/t"})
        try:
            corpus = EligibleCorpus({}, set(), [], kg=kg)
            result = corpus.kg_lookup("Hf ductility")
            self.assertTrue(result["facts"])
            for fact in result["facts"]:
                record = corpus.lookup[fact["record_id"]]
                self.assertEqual(record.kind, "kg_cooccurrence")
                self.assertLess(record.publication_date, "2021-03-01")
                self.assertFalse(record.paper_id.startswith("10.1/t"))
            self.assertEqual(corpus.read(result["facts"][0]["record_id"])["kind"], "kg_cooccurrence")
        finally:
            kg.close()

    def test_kg_fact_must_be_read_before_it_is_cited(self) -> None:
        kg = TemporalKG(self.db, "2021-03-01", {"10.1/t"})
        try:
            corpus = EligibleCorpus({}, set(), [], kg=kg)
            state: dict[str, str] = {}

            def scripted(messages, tools):
                results = [m for m in messages if m.get("role") == "tool"]
                count = len(results)
                if count == 0:
                    name, args = "kg_lookup", {"topic": "Hf ductility"}
                elif count == 1:
                    state["rid"] = json.loads(results[-1]["content"])["facts"][0]["record_id"]
                    name, args = "submit_hypothesis", {"hypothesis": self._hypothesis([state["rid"]])}
                elif count == 2:
                    name, args = "read_record", {"record_id": state["rid"]}
                else:
                    name, args = "submit_hypothesis", {"hypothesis": self._hypothesis([state["rid"]])}
                return {"content": "", "tool_calls": [{
                    "id": f"c{count}", "type": "function",
                    "function": {"name": name, "arguments": json.dumps(args)},
                }]}

            result = run_tool_agent("query", "2021-03-01", corpus, call_model=scripted, kg_enabled=True)
            rejected = [step for step in result["trace"] if step.get("accepted") is False]
            self.assertEqual(len(rejected), 1)
            self.assertEqual(result["generation"]["supporting_evidence_ids"], [state["rid"]])
            self.assertIn(state["rid"], corpus.read_ids)
        finally:
            kg.close()

    @staticmethod
    def _hypothesis(supporting: list[str]) -> dict[str, object]:
        return {"hypothesis": "Hf and Nb raise hardness.", "supporting_evidence_ids": supporting,
                "conflicting_evidence_ids": []}

    def test_audit_handles_kg_records_and_flags_post_cutoff_dates(self) -> None:
        metadata = {"T": {"doi": "10.1/t", "work_family_id": "fam-1"}}
        ok = RetrievalRecord("KG::nb::1", "matkg:1", "2019-12-31", "kg_cooccurrence", "text", {})
        late = RetrievalRecord("KG::nb::2", "matkg:2", "2021-12-31", "kg_cooccurrence", "text", {})
        counts = audit_accessed(["KG::nb::1", "KG::nb::2"], {r.record_id: r for r in (ok, late)}, "T", "2021-03-01", metadata)
        self.assertEqual(counts["temporal_violations"], 1)
        self.assertEqual(counts["test_paper_leaks"], 0)
        self.assertEqual(counts["family_leaks"], 0)


if __name__ == "__main__":
    unittest.main()
