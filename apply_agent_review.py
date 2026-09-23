"""Apply agent review operations to curated extraction claims."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def apply_review(payload: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    if payload["paper_id"] != review["paper_id"]:
        raise ValueError("paper_id mismatch")
    claims = [dict(claim) for claim in payload["claims"]]
    remove = set(review.get("remove_evidence_spans", []))
    claims = [claim for claim in claims if claim["evidence_span"] not in remove]
    by_evidence = {claim["evidence_span"]: claim for claim in claims}
    for operation in review.get("update", []):
        evidence = operation["evidence_span"]
        if evidence not in by_evidence:
            raise ValueError(f"claim not found for update: {evidence[:100]!r}")
        by_evidence[evidence].update({key: value for key, value in operation.items() if key != "evidence_span"})
    existing = {(claim["role"], claim["evidence_span"]) for claim in claims}
    for claim in review.get("add", []):
        key = (claim["role"], claim["evidence_span"])
        if key not in existing:
            claims.append(claim)
            existing.add(key)
    return {"paper_id": payload["paper_id"], "claims": claims}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims-dir", required=True, type=Path)
    parser.add_argument("--review-dir", required=True, type=Path)
    args = parser.parse_args()
    pending: list[tuple[Path, dict[str, Any], int]] = []
    for review_path in sorted(args.review_dir.glob("*.json")):
        review = json.loads(review_path.read_text())
        claims_path = args.claims_dir / review_path.name
        payload = json.loads(claims_path.read_text())
        updated = apply_review(payload, review)
        pending.append((claims_path, updated, len(payload["claims"])))
    for claims_path, updated, previous_count in pending:
        claims_path.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n")
        print(f"[review] {updated['paper_id']}: {previous_count} -> {len(updated['claims'])} claims")


if __name__ == "__main__":
    main()