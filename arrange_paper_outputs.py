"""Arrange one folder per paper and download checksum-verified PMC PDFs."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

PDF_NOTICE = """# Input files

- `article.xml` is the machine-readable source used by the data pipeline.
- `article.pdf` is included **only for visual inspection by a human reader**.

The PDF is not parsed, extracted, scored, or used as evidence by the pipeline. Exact grounding is
validated against the structure-preserving text generated from the JATS XML.
"""


def _http_json(url: str, retries: int = 3) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "MatHG/1.0"})
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.load(response)
        except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as error:
            last_error = error
            if isinstance(error, urllib.error.HTTPError) and error.code == 404:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError(f"metadata request failed after {retries} attempts: {last_error}")


def _resolve_metadata(paper_id: str) -> dict[str, Any]:
    versions: list[dict[str, Any]] = []
    for version in range(1, 11):
        url = (
            "https://pmc-oa-opendata.s3.amazonaws.com/metadata/"
            f"{paper_id}.{version}.json"
        )
        try:
            metadata = _http_json(url)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                if versions:
                    break
                continue
            raise
        if metadata.get("pdf_url"):
            versions.append(metadata)
    if not versions:
        raise RuntimeError(f"PMC OA metadata has no downloadable PDF for {paper_id}")
    published = [item for item in versions if not item.get("is_manuscript")]
    return max(published or versions, key=lambda item: int(item["version"]))


def _https_s3_url(s3_url: str) -> str:
    parsed = urllib.parse.urlsplit(s3_url)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError(f"unsupported PDF URL: {s3_url}")
    return urllib.parse.urlunsplit((
        "https",
        f"{parsed.netloc}.s3.amazonaws.com",
        parsed.path,
        parsed.query,
        "",
    ))


def _download_pdf(metadata: dict[str, Any], destination: Path) -> None:
    pdf_url = str(metadata["pdf_url"])
    expected_md5 = urllib.parse.parse_qs(
        urllib.parse.urlsplit(pdf_url).query
    ).get("md5", [""])[0]
    temporary = destination.with_suffix(".pdf.tmp")
    request = urllib.request.Request(
        _https_s3_url(pdf_url),
        headers={"User-Agent": "MatHG/1.0"},
    )
    digest = hashlib.md5()  # noqa: S324 - verifies the publisher-provided object checksum
    with urllib.request.urlopen(request, timeout=300) as response, temporary.open("wb") as output:
        prefix = response.read(5)
        if prefix != b"%PDF-":
            raise ValueError(
                f"download for {metadata['pmcid']} is not a PDF: prefix={prefix!r}"
            )
        output.write(prefix)
        digest.update(prefix)
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
    if expected_md5 and digest.hexdigest() != expected_md5:
        temporary.unlink(missing_ok=True)
        raise ValueError(
            f"PDF checksum mismatch for {metadata['pmcid']}: "
            f"expected {expected_md5}, got {digest.hexdigest()}"
        )
    temporary.replace(destination)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def arrange_paper(
    manifest_row: dict[str, Any],
    corpus_dir: Path,
    role_dir: Path,
    papers_dir: Path,
) -> tuple[str, int]:
    paper_id = str(manifest_row["paper_id"])
    xml_source = corpus_dir / "xml" / f"{paper_id}.xml"
    role_source = role_dir / f"{paper_id}.json"
    paper_dir = papers_dir / paper_id
    input_dir = paper_dir / "input"
    output_dir = paper_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    arranged_xml = input_dir / "article.xml"
    if xml_source.exists():
        if xml_source.resolve() != arranged_xml.resolve():
            shutil.copyfile(xml_source, arranged_xml)
    elif not arranged_xml.exists():
        raise FileNotFoundError(
            f"missing both source and arranged XML for {paper_id}: {xml_source}"
        )
    (input_dir / "README.md").write_text(PDF_NOTICE)

    if role_source.exists():
        role_record = json.loads(role_source.read_text())
    else:
        roles_path = output_dir / "roles.json"
        questions_path = output_dir / "questions.json"
        rejected_path = output_dir / "rejected_items.json"
        if not all(path.exists() for path in (roles_path, questions_path, rejected_path)):
            raise FileNotFoundError(
                f"missing both combined and split role/question outputs for {paper_id}"
            )
        role_record = {
            **json.loads(roles_path.read_text()),
            **json.loads(questions_path.read_text()),
            **json.loads(rejected_path.read_text()),
        }

    metadata = _resolve_metadata(paper_id)
    pdf_path = input_dir / "article.pdf"
    _download_pdf(metadata, pdf_path)

    _write_json(paper_dir / "metadata.json", {
        **manifest_row,
        "pmc_version": metadata["version"],
        "pdf_source": metadata["pdf_url"],
        "pdf_use": "visual inspection only; not used by the data pipeline",
    })
    _write_json(output_dir / "roles.json", {
        "schema_version": role_record.get("schema_version"),
        "paper_id": paper_id,
        "chunks_processed": role_record.get("chunks_processed"),
        "raw_by_role": role_record.get("raw_by_role", {}),
        "reconciled_by_role": role_record.get("reconciled_by_role", {}),
    })
    _write_json(output_dir / "questions.json", {
        "schema_version": role_record.get("schema_version"),
        "paper_id": paper_id,
        "questions": role_record.get("questions", []),
    })
    _write_json(output_dir / "rejected_items.json", {
        "schema_version": role_record.get("schema_version"),
        "paper_id": paper_id,
        "rejected_items": role_record.get("rejected_items", []),
    })
    return paper_id, pdf_path.stat().st_size


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", required=True, type=Path)
    parser.add_argument("--role-dir", required=True, type=Path)
    parser.add_argument("--papers-dir", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    manifest = json.loads((args.corpus_dir / "manifest.json").read_text())
    if not isinstance(manifest, list):
        raise ValueError("corpus manifest must be a list")
    args.papers_dir.mkdir(parents=True, exist_ok=True)
    failures: list[tuple[str, Exception]] = []
    total_bytes = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                arrange_paper,
                row,
                args.corpus_dir,
                args.role_dir,
                args.papers_dir,
            ): str(row["paper_id"])
            for row in manifest
        }
        for future in as_completed(futures):
            paper_id = futures[future]
            try:
                _, pdf_bytes = future.result()
            except Exception as error:
                failures.append((paper_id, error))
                print(f"[arrange-papers] ERROR {paper_id}: {error}")
                continue
            total_bytes += pdf_bytes
            print(f"[arrange-papers] {paper_id}: pdf_bytes={pdf_bytes}")
    if failures:
        for paper_id, error in failures:
            print(f"[arrange-papers] FAILED {paper_id}: {error}")
        raise SystemExit(1)
    print(
        f"[arrange-papers] complete papers={len(manifest)} "
        f"pdf_bytes={total_bytes}"
    )


if __name__ == "__main__":
    main()
