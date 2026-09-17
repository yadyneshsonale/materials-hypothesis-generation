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

from extract import extract_paper, record_to_dict
from llm_client import provider_info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input_dir", required=True, type=Path)
    ap.add_argument("--out_dir", required=True, type=Path)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max_passes", type=int, default=1, help="0 retries until every paper succeeds")
    ap.add_argument("--retry_delay", type=int, default=60, help="seconds between retry passes")
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(args.input_dir.glob("*.txt"))
    if args.limit:
        files = files[: args.limit]

    print(f"[mathg] provider={provider_info()} papers={len(files)}", file=sys.stderr)

    pass_number = 0
    while True:
        pass_number += 1
        pending = [f for f in files if not (args.out_dir / f"{f.stem}.json").exists()]
        if not pending:
            print(f"[mathg] all {len(files)} papers complete", file=sys.stderr)
            return

        print(f"[mathg] pass={pass_number} pending={len(pending)}", file=sys.stderr)
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

        remaining = sum(not (args.out_dir / f"{f.stem}.json").exists() for f in files)
        if not remaining:
            print(f"[mathg] all {len(files)} papers complete", file=sys.stderr)
            return
        if args.max_passes and pass_number >= args.max_passes:
            print(f"[mathg] ERROR: {remaining} papers remain after {pass_number} passes", file=sys.stderr)
            raise SystemExit(1)
        print(f"[mathg] {remaining} papers remain; retrying in {args.retry_delay}s", file=sys.stderr)
        time.sleep(args.retry_delay)


if __name__ == "__main__":
    main()
