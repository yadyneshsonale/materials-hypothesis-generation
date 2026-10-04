from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from temporal_metadata import (
    build_temporal_audit,
    parse_jats_temporal_metadata,
    write_atomic_json,
)


JATS = """\
<article xmlns="urn:test">
  <front>
    <article-meta>
      <article-id pub-id-type="doi">https://doi.org/10.1000/ABC</article-id>
      <pub-date pub-type="epub"><day>5</day><month>2</month><year>2024</year></pub-date>
      <pub-date pub-type="collection"><month>2</month><year>2024</year></pub-date>
      <pub-date pub-type="ppub"><day>10</day><month>2</month><year>2024</year></pub-date>
      <pub-history>
        <event event-type="pmc-release">
          <date><day>7</day><month>2</month><year>2024</year></date>
        </event>
      </pub-history>
    </article-meta>
  </front>
</article>
"""


class TemporalMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.papers_dir = self.root / "papers"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _write_paper(self, paper_id: str, xml: str = JATS) -> Path:
        xml_path = self.papers_dir / paper_id / "input" / "article.xml"
        xml_path.parent.mkdir(parents=True)
        xml_path.write_text(xml, encoding="utf-8")
        return xml_path

    def _write_manifest(self, rows: list[dict[str, object]]) -> Path:
        path = self.root / "manifest.json"
        path.write_text(json.dumps(rows), encoding="utf-8")
        return path

    def test_parses_only_exact_dates_and_preserves_sources(self) -> None:
        xml_path = self._write_paper("PMC1")

        dates = parse_jats_temporal_metadata(xml_path)

        self.assertEqual(dates["online_publication_date"], "2024-02-05")
        self.assertIsNone(dates["collection_publication_date"])
        self.assertEqual(dates["print_publication_date"], "2024-02-10")
        self.assertEqual(dates["pmc_release_date"], "2024-02-07")

    def test_merges_manifest_and_flags_post_cutoff_leakage(self) -> None:
        self._write_paper("PMC1")
        manifest = self._write_manifest([{
            "paper_id": "PMC1",
            "title": "Alloy study",
            "doi": "DOI: 10.1000/ABC",
            "preprint_doi": "10.5555/PREPRINT",
        }])

        audit = build_temporal_audit(
            manifest, self.papers_dir, date(2024, 2, 4)
        )
        paper = audit["papers"][0]

        self.assertEqual(audit["model_cutoff_status"], "documented")
        self.assertEqual(paper["title"], "Alloy study")
        self.assertEqual(paper["earliest_public_date"], "2024-02-05")
        self.assertEqual(
            paper["earliest_public_date_source"], "online_publication_date"
        )
        self.assertEqual(paper["cutoff_eligibility"], "ineligible")
        self.assertFalse(paper["eligible_at_model_cutoff"])
        self.assertTrue(paper["potential_temporal_leakage"])
        self.assertEqual(paper["work_family_id"], "doi:10.1000/abc")
        self.assertEqual(
            paper["work_family_identifiers"],
            ["doi:10.1000/abc", "doi:10.5555/preprint"],
        )

    def test_unknown_cutoff_is_explicit_and_not_false_safety(self) -> None:
        self._write_paper("PMC1")
        manifest = self._write_manifest([{"paper_id": "PMC1"}])

        audit = build_temporal_audit(manifest, self.papers_dir)
        paper = audit["papers"][0]

        self.assertEqual(audit["model_cutoff_status"], "unknown_undocumented")
        self.assertIsNone(audit["model_cutoff"])
        self.assertEqual(paper["cutoff_eligibility"], "unknown")
        self.assertIsNone(paper["eligible_at_model_cutoff"])
        self.assertEqual(paper["temporal_leakage"], "unknown")
        self.assertIsNone(paper["potential_temporal_leakage"])

    def test_family_fallback_does_not_invent_a_relationship(self) -> None:
        no_doi = JATS.replace(
            '<article-id pub-id-type="doi">https://doi.org/10.1000/ABC</article-id>',
            "",
        )
        self._write_paper("PMC1", no_doi)
        manifest = self._write_manifest([{"paper_id": "PMC1"}])

        paper = build_temporal_audit(manifest, self.papers_dir)["papers"][0]

        self.assertEqual(paper["work_family_id"], "paper:PMC1")
        self.assertEqual(paper["work_family_basis"], "paper_id_fallback")
        self.assertEqual(paper["work_family_identifiers"], [])

    def test_atomic_writer_emits_valid_json_without_temporary_file(self) -> None:
        output = self.root / "nested" / "audit.json"
        payload = {"papers": [{"paper_id": "PMC1"}]}

        write_atomic_json(output, payload)

        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), payload)
        self.assertEqual(list(output.parent.glob(".audit.json.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
