"""CLI entrypoint: run Stage-1 role extraction over a directory of paper text files.

Usage:
  python run_extraction.py --input_dir texts/ --out_dir outputs/ [--limit 10]

Each <paper_id>.txt in input_dir is processed independently; output is written
to out_dir/<paper_id>.json. Provider is selected via env vars (see llm_client.py);
with no credentials configured it runs in "dryrun" mode so the plumbing can be
smoke-tested without any API access.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from build_evidence_graph import _title_from_source, _validate_bundle, aggregate, build_paper
from extract import extract_paper, record_to_dict
from llm_client import provider_info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input_dir", required=True, type=Path)
    ap.add_argument("--out_dir", required=True, type=Path)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max_passes", type=int, default=1, help="0 retries until every paper succeeds")
    ap.add_argument("--retry_delay", type=int, default=60, help="seconds between retry passes")
    ap.add_argument("--evidence_graph_dir", type=Path, help="normalize each completed paper into typed entities and relations")
    ap.add_argument("--metadata", type=Path, help="optional paper-title metadata JSON for evidence entities")
    ap.add_argument("--evidence_normalizer", choices=("deterministic", "llm"), default="deterministic")
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(args.input_dir.glob("*.txt"))
    if args.limit:
        files = files[: args.limit]

    metadata = json.loads(args.metadata.read_text()) if args.metadata else {}
    titles = {
        f.stem: _title_from_source(f.stem, f.read_text(encoding="utf-8", errors="ignore"), metadata)
        for f in files
    }
    evidence_paper_dir = args.evidence_graph_dir / "papers" if args.evidence_graph_dir else None
    if evidence_paper_dir:
        evidence_paper_dir.mkdir(parents=True, exist_ok=True)

    def normalize_paper(source_path: Path, output_path: Path) -> bool:
        if evidence_paper_dir is None:
            return True
        destination = evidence_paper_dir / output_path.name
        if destination.exists():
            return True
        try:
            bundle = build_paper(output_path, source_path, titles[source_path.stem], args.evidence_normalizer)
            _validate_bundle(bundle)
            temporary = destination.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(bundle, indent=2))
            temporary.replace(destination)
            print(f"[evidence] {source_path.stem}: entities={len(bundle['entities'])} relations={len(bundle['relations'])}", file=sys.stderr)
            return True
        except Exception as e:  # noqa: BLE001 - retry normalization without repeating extraction
            print(f"[evidence] ERROR: {source_path.stem} normalization failed: {e}", file=sys.stderr)
            return False

    print(f"[mathg] provider={provider_info()} papers={len(files)}", file=sys.stderr)

    pass_number = 0
    while True:
        pass_number += 1
        pending = [f for f in files if not (args.out_dir / f"{f.stem}.json").exists()]
        evidence_pending = [
            f for f in files
            if evidence_paper_dir and (args.out_dir / f"{f.stem}.json").exists()
            and not (evidence_paper_dir / f"{f.stem}.json").exists()
        ]
        if not pending and not evidence_pending:
            if args.evidence_graph_dir:
                entity_count, relation_count = aggregate(args.evidence_graph_dir, titles, args.input_dir, args.evidence_normalizer)
                print(f"[evidence] aggregate entities={entity_count} relations={relation_count}", file=sys.stderr)
            print(f"[mathg] all {len(files)} papers complete", file=sys.stderr)
            return

        print(f"[mathg] pass={pass_number} extraction_pending={len(pending)} evidence_pending={len(evidence_pending)}", file=sys.stderr)
        for f in pending:
            paper_id = f.stem
            out_path = args.out_dir / f"{paper_id}.json"
            text = f.read_text(encoding="utf-8", errors="ignore")
            try:
                record = extract_paper(paper_id, text)
            except Exception as e:  # noqa: BLE001 - retry failed papers on the next pass
                print(f"[mathg] ERROR: {paper_id} failed: {e}", file=sys.stderr)
                continue
            out_path.write_text(json.dumps(record_to_dict(record), indent=2))
            n_found = sum(len(v) for v in record.raw_by_role.values())
            print(f"[mathg] {paper_id}: {record.chunks_processed} chunks, {n_found} raw items -> {out_path}", file=sys.stderr)
            normalize_paper(f, out_path)

        for f in evidence_pending:
            normalize_paper(f, args.out_dir / f"{f.stem}.json")

        remaining_extraction = sum(not (args.out_dir / f"{f.stem}.json").exists() for f in files)
        remaining_evidence = sum(
            not (evidence_paper_dir / f"{f.stem}.json").exists() for f in files
        ) if evidence_paper_dir else 0
        remaining = remaining_extraction + remaining_evidence
        if not remaining:
            continue
        if args.max_passes and pass_number >= args.max_passes:
            print(f"[mathg] ERROR: {remaining} papers remain after {pass_number} passes", file=sys.stderr)
            raise SystemExit(1)
        print(f"[mathg] {remaining} papers remain; retrying in {args.retry_delay}s", file=sys.stderr)
        time.sleep(args.retry_delay)


if __name__ == "__main__":
    main()
