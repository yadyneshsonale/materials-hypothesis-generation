"""Package paper assets and per-paper questions into numbered output folders."""
from __future__ import annotations

import argparse
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


PIPELINES = {
    "question_centered": {
        "source": "question_centered/resolved_questions",
        "description": "Resolved reader questions, grounded answers, and scientific facets.",
    },
    "section_aware": {
        "source": "section_aware/papers",
        "description": "Cross-section questions, validated links, and research threads.",
    },
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _question_count(pipeline: str, payload: dict[str, Any]) -> int:
    if pipeline == "question_centered":
        return len(payload.get("questions", []))
    return sum(
        len(trigger.get("questions", []))
        for trigger in payload.get("triggers", [])
    )


def package_pipeline(
    experiment_root: Path,
    manifest_path: Path,
    pipeline: str,
) -> dict[str, Any]:
    if pipeline not in PIPELINES:
        raise ValueError(f"unknown pipeline={pipeline}")
    manifest = _read_json(manifest_path)
    if not isinstance(manifest, list):
        raise ValueError("manifest must be a list")
    ranks = sorted(int(row["rank"]) for row in manifest)
    if ranks != list(range(1, 51)):
        raise ValueError("manifest must contain each rank from 1 through 50 exactly once")

    config = PIPELINES[pipeline]
    pipeline_root = experiment_root / pipeline
    source_dir = experiment_root / config["source"]
    output_dir = pipeline_root / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    packaged = []

    for row in sorted(manifest, key=lambda item: int(item["rank"])):
        rank = int(row["rank"])
        paper_id = str(row["paper_id"])
        source_assets = experiment_root / "outputs" / "papers" / paper_id / "input"
        source_questions = source_dir / f"{paper_id}.json"
        required = (
            source_assets / "article.pdf",
            source_assets / "article.xml",
            source_questions,
        )
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"missing inputs for rank {rank}: {missing}")

        destination = output_dir / str(rank)
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(required[0], destination / "paper.pdf")
        shutil.copy2(required[1], destination / "paper.xml")
        shutil.copy2(source_questions, destination / "extracted_questions.json")

        question_payload = _read_json(source_questions)
        if question_payload.get("paper_id") != paper_id:
            raise ValueError(
                f"question output paper mismatch at rank {rank}: "
                f"{question_payload.get('paper_id')} != {paper_id}"
            )
        metadata = {
            "rank": rank,
            "paper_id": paper_id,
            "title": row.get("title"),
            "doi": row.get("doi"),
            "publication_year": row.get("publication_year"),
            "citation_count": row.get("citation_count"),
            "license": row.get("license"),
            "pipeline": pipeline,
            "pipeline_description": config["description"],
            "question_count": _question_count(pipeline, question_payload),
            "files": {
                "pdf": "paper.pdf",
                "xml": "paper.xml",
                "questions": "extracted_questions.json",
            },
            "canonical_sources": {
                "paper_assets": str(source_assets),
                "question_output": str(source_questions),
            },
        }
        (destination / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"
        )
        packaged.append(metadata)

    index = {
        "schema_version": "numbered-pipeline-outputs-1.0",
        "pipeline": pipeline,
        "paper_count": len(packaged),
        "papers": packaged,
    }
    (output_dir / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n"
    )
    return index


def validate_pipeline(
    experiment_root: Path,
    manifest_path: Path,
    pipeline: str,
) -> dict[str, Any]:
    manifest = {
        int(row["rank"]): str(row["paper_id"])
        for row in _read_json(manifest_path)
    }
    output_dir = experiment_root / pipeline / "outputs"
    errors = []
    question_total = 0
    for rank in range(1, 51):
        directory = output_dir / str(rank)
        paths = {
            "pdf": directory / "paper.pdf",
            "xml": directory / "paper.xml",
            "questions": directory / "extracted_questions.json",
            "metadata": directory / "metadata.json",
        }
        for kind, path in paths.items():
            if not path.is_file() or path.stat().st_size == 0:
                errors.append(f"rank {rank}: missing or empty {kind}")
        if any(not path.is_file() for path in paths.values()):
            continue
        metadata = _read_json(paths["metadata"])
        questions = _read_json(paths["questions"])
        expected_paper = manifest.get(rank)
        if metadata.get("rank") != rank:
            errors.append(f"rank {rank}: metadata rank mismatch")
        if metadata.get("paper_id") != expected_paper:
            errors.append(f"rank {rank}: metadata paper mismatch")
        if questions.get("paper_id") != expected_paper:
            errors.append(f"rank {rank}: question paper mismatch")
        count = _question_count(pipeline, questions)
        question_total += count
        if metadata.get("question_count") != count:
            errors.append(f"rank {rank}: question count mismatch")
        if not paths["pdf"].read_bytes().startswith(b"%PDF"):
            errors.append(f"rank {rank}: invalid PDF signature")
        try:
            xml_root = ET.parse(paths["xml"]).getroot()
        except ET.ParseError:
            errors.append(f"rank {rank}: XML is not well formed")
        else:
            if xml_root.tag.rsplit("}", 1)[-1] != "article":
                errors.append(f"rank {rank}: XML root is not article")

    index_path = output_dir / "index.json"
    if not index_path.is_file():
        errors.append("missing outputs/index.json")
    else:
        index = _read_json(index_path)
        if index.get("paper_count") != 50:
            errors.append("index paper count mismatch")
        if index.get("pipeline") != pipeline:
            errors.append("index pipeline mismatch")

    result = {
        "pipeline": pipeline,
        "paper_folders": 50,
        "question_count": question_total,
        "errors": errors,
        "verified": not errors,
    }
    if errors:
        raise ValueError(f"numbered output validation failed: {result}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--experiment-root",
        type=Path,
        default=Path("experiments/high_temperature_hea_qwen35b"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(
            "experiments/high_temperature_hea_qwen35b/data/corpus/manifest.json"
        ),
    )
    parser.add_argument(
        "--pipeline",
        choices=tuple(PIPELINES),
        action="append",
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    pipelines = args.pipeline or list(PIPELINES)
    results = []
    for pipeline in pipelines:
        if not args.validate_only:
            package_pipeline(
                args.experiment_root,
                args.manifest,
                pipeline,
            )
        results.append(validate_pipeline(
            args.experiment_root,
            args.manifest,
            pipeline,
        ))
    print(json.dumps({"pipelines": results}, indent=2))


if __name__ == "__main__":
    main()
