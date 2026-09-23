"""Download screened Europe PMC JATS papers and convert them to extraction text."""
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any

import requests

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
REVIEW_TYPES = {"review", "review-article", "systematic review", "meta-analysis"}
REVIEW_TITLE_RE = re.compile(r"\b(review|survey|perspective|roadmap|bibliometric)\b", re.I)
EMPIRICAL_HEADING_RE = re.compile(r"\b(method|material|experiment|result)\w*\b", re.I)


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _text(element: ET.Element | None, reference_numbers: dict[str, str] | None = None) -> str:
    if element is None:
        return ""
    if reference_numbers is None:
        return " ".join(" ".join(element.itertext()).split())
    fragments = [element.text or ""]
    for child in element:
        if _tag(child) == "xref" and child.get("ref-type") == "bibr":
            numbers = [reference_numbers[rid] for rid in child.get("rid", "").split() if rid in reference_numbers]
            fragments.append(f"[{', '.join(numbers)}]" if numbers else _text(child, reference_numbers))
        else:
            fragments.append(_text(child, reference_numbers))
        fragments.append(child.tail or "")
    return " ".join(" ".join(fragments).split())


def _reference_numbers(root: ET.Element) -> dict[str, str]:
    numbers = {}
    for index, reference in enumerate(root.findall(".//ref-list/ref"), start=1):
        match = re.search(r"\d+", _text(reference.find("label")))
        numbers[reference.get("id", "")] = match.group() if match else str(index)
    return numbers


def fetch_metadata(pmcid: str) -> dict[str, Any]:
    response = requests.get(
        f"{EUROPE_PMC}/search",
        params={"query": f"PMCID:{pmcid}", "format": "json", "resultType": "core"},
        timeout=60,
    )
    response.raise_for_status()
    rows = response.json().get("resultList", {}).get("result", [])
    if len(rows) != 1:
        raise ValueError(f"expected one Europe PMC record for {pmcid}, found {len(rows)}")
    return rows[0]


def fetch_xml(pmcid: str) -> bytes:
    response = requests.get(f"{EUROPE_PMC}/{pmcid}/fullTextXML", timeout=60)
    response.raise_for_status()
    return response.content


def validate_primary_research(root: ET.Element, metadata: dict[str, Any]) -> dict[str, Any]:
    title = _text(root.find(".//article-title"))
    publication_types = {
        str(value).lower() for value in metadata.get("pubTypeList", {}).get("pubType", [])
    }
    categories = [_text(value) for value in root.findall(".//article-categories//subject")]
    headings = [_text(value) for value in root.findall(".//body//sec/title")]
    empirical_headings = [heading for heading in headings if EMPIRICAL_HEADING_RE.search(heading)]
    review_reasons = []
    if publication_types & REVIEW_TYPES:
        review_reasons.append("review publication type")
    if REVIEW_TITLE_RE.search(title):
        review_reasons.append("review/survey title")
    if "research-article" not in publication_types:
        review_reasons.append("not indexed as research-article")
    if not empirical_headings:
        review_reasons.append("no methods/results-style section")
    if review_reasons:
        raise ValueError(f"{metadata.get('pmcid') or metadata.get('id')}: " + "; ".join(review_reasons))
    return {
        "publication_types": sorted(publication_types),
        "article_categories": categories,
        "empirical_headings": empirical_headings,
        "screened_as_primary_research": True,
        "survey_or_review": False,
    }


def jats_to_text(root: ET.Element) -> str:
    lines: list[str] = []
    reference_numbers = _reference_numbers(root)
    title = _text(root.find(".//article-title"))
    if title:
        lines.extend([title, ""])
    abstract = root.find(".//abstract")
    if abstract is not None:
        lines.extend(["Abstract", _text(abstract, reference_numbers), ""])

    body = root.find(".//body")
    if body is not None:
        parents = {child: parent for parent in body.iter() for child in parent}

        def inside_table(element: ET.Element) -> bool:
            parent = parents.get(element)
            while parent is not None:
                if parent.tag.rsplit("}", 1)[-1] == "table-wrap":
                    return True
                parent = parents.get(parent)
            return False

        for element in body.iter():
            tag = _tag(element)
            if tag == "sec":
                heading = _text(element.find("title"))
                if heading:
                    lines.extend([heading, ""])
            elif tag == "p" and not inside_table(element):
                paragraph = _text(element, reference_numbers)
                if paragraph:
                    lines.extend([paragraph, ""])
            elif tag == "table-wrap":
                label = _text(element.find("label")) or "Table"
                caption = _text(element.find("caption"), reference_numbers)
                lines.append(f"{label}. {caption}".strip())
                for row in element.findall(".//tr"):
                    cells = [_text(cell, reference_numbers) for cell in list(row) if _tag(cell) in {"th", "td"}]
                    if cells:
                        lines.append("\t".join(cells))
                lines.append("")

    references = root.findall(".//ref-list/ref")
    if references:
        lines.extend(["References", ""])
        for index, reference in enumerate(references, start=1):
            label = reference_numbers.get(reference.get("id", ""), str(index))
            citation = reference.find("element-citation")
            if citation is None:
                citation = reference.find("mixed-citation")
            lines.append(f"[{label}] {_text(citation or reference)}")
    return "\n".join(lines).strip() + "\n"


def import_corpus(pmcids: list[str], corpus_dir: Path) -> list[dict[str, Any]]:
    xml_dir = corpus_dir / "xml"
    text_dir = corpus_dir / "text"
    xml_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for rank, pmcid in enumerate(pmcids, start=1):
        metadata = fetch_metadata(pmcid)
        xml_bytes = fetch_xml(pmcid)
        root = ET.fromstring(xml_bytes)
        screening = validate_primary_research(root, metadata)
        title = _text(root.find(".//article-title"))
        xml_path = xml_dir / f"{pmcid}.xml"
        text_path = text_dir / f"{pmcid}.txt"
        xml_path.write_bytes(xml_bytes)
        text_path.write_text(jats_to_text(root), encoding="utf-8")
        manifest.append({
            "rank": rank,
            "paper_id": pmcid,
            "title": title,
            "doi": metadata.get("doi", ""),
            "citation_count": int(metadata.get("citedByCount") or 0),
            "citation_count_source": "Europe PMC",
            "citation_count_checked": date.today().isoformat(),
            "license": metadata.get("license", ""),
            "xml_source": f"{EUROPE_PMC}/{pmcid}/fullTextXML",
            **screening,
        })
        print(f"[jats] {rank:02d} {pmcid}: citations={manifest[-1]['citation_count']} {title}")
    (corpus_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    metadata = {
        row["paper_id"]: {"title": row["title"], "doi": row["doi"], "license": row["license"]}
        for row in manifest
    }
    (corpus_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", required=True, type=Path)
    parser.add_argument("pmcids", nargs="+")
    args = parser.parse_args()
    import_corpus(args.pmcids, args.corpus_dir)


if __name__ == "__main__":
    main()