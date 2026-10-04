"""Audit exact JATS publication dates and model-cutoff leakage metadata."""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any, Iterable


DATE_FIELDS = (
    "online_publication_date",
    "collection_publication_date",
    "print_publication_date",
    "pmc_release_date",
)
PUBLIC_DATE_FIELDS = DATE_FIELDS
ONLINE_TYPES = {"epub", "electronic", "online"}
PRINT_TYPES = {"ppub", "print"}
DOI_PREFIX_RE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.I)


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> Iterable[ET.Element]:
    return (child for child in element if _tag(child) == name)


def _child_text(element: ET.Element, name: str) -> str:
    child = next(_children(element, name), None)
    return "".join(child.itertext()).strip() if child is not None else ""


def _exact_date(element: ET.Element) -> date | None:
    parts = {
        name: _child_text(element, name)
        for name in ("year", "month", "day")
    }
    if not all(parts.values()):
        return None
    try:
        return date(int(parts["year"]), int(parts["month"]), int(parts["day"]))
    except ValueError as error:
        raise ValueError(f"invalid JATS date components: {parts}") from error


def _one_date(candidates: Iterable[ET.Element], source: str) -> date | None:
    exact_dates = {value for element in candidates if (value := _exact_date(element))}
    if len(exact_dates) > 1:
        rendered = ", ".join(sorted(value.isoformat() for value in exact_dates))
        raise ValueError(f"conflicting exact dates for {source}: {rendered}")
    return next(iter(exact_dates), None)


def _article_meta(root: ET.Element) -> ET.Element:
    for element in root.iter():
        if _tag(element) == "article-meta":
            return element
    raise ValueError("JATS XML has no article-meta element")


def parse_jats_temporal_metadata(xml_path: Path) -> dict[str, str | None]:
    """Return exact publication dates from one JATS article."""
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as error:
        raise ValueError(f"invalid JATS XML in {xml_path}: {error}") from error

    article_meta = _article_meta(root)
    pub_dates = [
        element
        for element in article_meta.iter()
        if _tag(element) == "pub-date"
    ]
    typed_online = [
        element
        for element in pub_dates
        if element.get("pub-type", "").lower() in ONLINE_TYPES
    ]
    untyped = [element for element in pub_dates if not element.get("pub-type")]
    online_candidates = typed_online if typed_online else untyped
    collection_candidates = [
        element
        for element in pub_dates
        if element.get("pub-type", "").lower() == "collection"
    ]
    print_candidates = [
        element
        for element in pub_dates
        if element.get("pub-type", "").lower() in PRINT_TYPES
    ]
    pmc_release_candidates = [
        date_element
        for event in article_meta.iter()
        if _tag(event) == "event"
        and event.get("event-type", "").lower() == "pmc-release"
        for date_element in _children(event, "date")
    ]

    values = {
        "online_publication_date": _one_date(
            online_candidates, "online publication"
        ),
        "collection_publication_date": _one_date(
            collection_candidates, "collection publication"
        ),
        "print_publication_date": _one_date(
            print_candidates, "print publication"
        ),
        "pmc_release_date": _one_date(pmc_release_candidates, "PMC release"),
    }
    return {
        field: value.isoformat() if value is not None else None
        for field, value in values.items()
    }


def _normalize_doi(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = DOI_PREFIX_RE.sub("", value.strip()).lower()
    return normalized or None


def _explicit_preprint_identifiers(metadata: dict[str, Any]) -> list[str]:
    identifiers: list[str] = []
    preprint = metadata.get("preprint")
    candidates = [
        metadata.get("preprint_doi"),
        metadata.get("preprint_id"),
        metadata.get("preprint_identifier"),
    ]
    if isinstance(preprint, dict):
        candidates.extend((preprint.get("doi"), preprint.get("id")))
    elif isinstance(preprint, str):
        candidates.append(preprint)

    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        raw = candidate.strip()
        normalized_doi = _normalize_doi(raw) if "10." in raw.lower() else None
        identifier = f"doi:{normalized_doi}" if normalized_doi else f"preprint:{raw}"
        if identifier not in identifiers:
            identifiers.append(identifier)
    return identifiers


def _xml_doi(xml_path: Path) -> str | None:
    root = ET.parse(xml_path).getroot()
    article_meta = _article_meta(root)
    for element in article_meta.iter():
        if (
            _tag(element) == "article-id"
            and element.get("pub-id-type", "").lower() == "doi"
        ):
            return _normalize_doi("".join(element.itertext()))
    return None


def _work_family(
    metadata: dict[str, Any], xml_path: Path, paper_id: str
) -> tuple[str, str, list[str]]:
    doi = _normalize_doi(metadata.get("doi")) or _xml_doi(xml_path)
    preprints = _explicit_preprint_identifiers(metadata)
    if doi:
        identifier = f"doi:{doi}"
        return identifier, "doi", [identifier, *preprints]
    if preprints:
        return preprints[0], "explicit_preprint_metadata", preprints
    return f"paper:{paper_id}", "paper_id_fallback", []


def _cutoff_fields(
    earliest: date | None, cutoff: date | None
) -> dict[str, Any]:
    if cutoff is None:
        return {
            "cutoff_eligibility": "unknown",
            "eligible_at_model_cutoff": None,
            "temporal_leakage": "unknown",
            "potential_temporal_leakage": None,
            "leakage_reason": "model cutoff is unknown or undocumented",
        }
    if earliest is None:
        return {
            "cutoff_eligibility": "unknown",
            "eligible_at_model_cutoff": None,
            "temporal_leakage": "unknown",
            "potential_temporal_leakage": None,
            "leakage_reason": "no exact public date is available",
        }
    eligible = earliest <= cutoff
    return {
        "cutoff_eligibility": "eligible" if eligible else "ineligible",
        "eligible_at_model_cutoff": eligible,
        "temporal_leakage": (
            "no_post_cutoff_publication_detected"
            if eligible
            else "potential_post_cutoff_leakage"
        ),
        "potential_temporal_leakage": not eligible,
        "leakage_reason": (
            f"earliest public date {earliest.isoformat()} "
            f"{'is on or before' if eligible else 'is after'} model cutoff "
            f"{cutoff.isoformat()}"
        ),
    }


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = payload.get("papers") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("manifest must be a JSON list or an object with a papers list")
    return rows


def build_temporal_audit(
    manifest_path: Path, papers_dir: Path, model_cutoff: date | None = None
) -> dict[str, Any]:
    """Merge manifest records with exact JATS dates and leakage flags."""
    papers: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for metadata in _load_manifest(manifest_path):
        paper_id = str(metadata.get("paper_id") or metadata.get("pmcid") or "").strip()
        if not paper_id:
            raise ValueError("every manifest record must have paper_id or pmcid")
        if paper_id in seen_ids:
            raise ValueError(f"duplicate paper ID in manifest: {paper_id}")
        seen_ids.add(paper_id)

        xml_path = papers_dir / paper_id / "input" / "article.xml"
        if not xml_path.is_file():
            raise FileNotFoundError(f"missing JATS XML for {paper_id}: {xml_path}")
        publication_dates = parse_jats_temporal_metadata(xml_path)
        dated_sources = [
            (date.fromisoformat(value), field)
            for field, value in publication_dates.items()
            if value is not None and field in PUBLIC_DATE_FIELDS
        ]
        earliest, earliest_source = (
            min(dated_sources) if dated_sources else (None, None)
        )
        work_family_id, work_family_basis, family_identifiers = _work_family(
            metadata, xml_path, paper_id
        )
        papers.append({
            **metadata,
            "paper_id": paper_id,
            **publication_dates,
            "earliest_public_date": earliest.isoformat() if earliest else None,
            "earliest_public_date_source": earliest_source,
            "work_family_id": work_family_id,
            "work_family_basis": work_family_basis,
            "work_family_identifiers": family_identifiers,
            **_cutoff_fields(earliest, model_cutoff),
        })

    return {
        "schema_version": 1,
        "model_cutoff": model_cutoff.isoformat() if model_cutoff else None,
        "model_cutoff_status": "documented" if model_cutoff else "unknown_undocumented",
        "paper_count": len(papers),
        "papers": papers,
    }


def write_atomic_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON by replacing the destination only after a complete flush."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = handle.name
            json.dump(payload, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        if temporary_path is not None:
            Path(temporary_path).unlink(missing_ok=True)
        raise


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"expected an exact date in YYYY-MM-DD format: {value}"
        ) from error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--papers-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model-cutoff", type=_iso_date, metavar="YYYY-MM-DD")
    args = parser.parse_args()

    audit = build_temporal_audit(
        args.manifest, args.papers_dir, args.model_cutoff
    )
    write_atomic_json(args.output, audit)


if __name__ == "__main__":
    main()
