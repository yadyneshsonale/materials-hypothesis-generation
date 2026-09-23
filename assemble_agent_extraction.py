"""Validate agent-curated claims and assemble Stage-1 extraction records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from chunking import split_into_chunks
from roles import ROLE_KEYS


def assemble(paper_id: str, text: str, claims: list[dict[str, Any]]) -> dict[str, Any]:
    raw = {role: [] for role in ROLE_KEYS}
    reconciled = {role: [] for role in ROLE_KEYS}
    seen: set[tuple[str, str]] = set()
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    group_metadata: dict[tuple[str, str], tuple[str, bool]] = {}
    for claim_index, claim in enumerate(claims):
        role = claim.get("role")
        content = str(claim.get("content", "")).strip()
        evidence = str(claim.get("evidence_span", "")).strip()
        if role not in raw:
            raise ValueError(f"unknown role: {role}")
        if not content or not evidence:
            raise ValueError(f"empty content or evidence for {paper_id}/{role}")
        if evidence not in text:
            raise ValueError(f"non-verbatim evidence for {paper_id}/{role}: {evidence[:100]!r}")
        key = (role, evidence)
        if key in seen:
            continue
        seen.add(key)
        item = {"role": role, "content": content, "evidence_span": evidence}
        raw[role].append(item)
        group_id = str(claim.get("reconcile_group") or f"claim-{claim_index}")
        group_key = (role, group_id)
        groups.setdefault(group_key, []).append(item)
        reconciled_content = str(claim.get("reconciled_content") or content).strip()
        conflicting = bool(claim.get("conflicting", False))
        previous = group_metadata.setdefault(group_key, (reconciled_content, conflicting))
        if previous[0] != reconciled_content:
            raise ValueError(f"inconsistent reconciled content for {paper_id}/{role}/{group_id}")
        group_metadata[group_key] = (reconciled_content, previous[1] or conflicting)
    for (role, group_id), items in groups.items():
        content, conflicting = group_metadata[(role, group_id)]
        reconciled[role].append({
            "content": content,
            "evidence_spans": [item["evidence_span"] for item in items],
            "conflicting": conflicting,
        })
    return {
        "paper_id": paper_id,
        "chunks_processed": len(split_into_chunks(text)),
        "raw_by_role": raw,
        "reconciled_by_role": reconciled,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text-dir", required=True, type=Path)
    parser.add_argument("--claims-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    pending: list[tuple[str, Path, dict[str, Any]]] = []
    for claims_path in sorted(args.claims_dir.glob("*.json")):
        payload = json.loads(claims_path.read_text())
        paper_id = payload["paper_id"]
        text = (args.text_dir / f"{paper_id}.txt").read_text()
        record = assemble(paper_id, text, payload["claims"])
        pending.append((paper_id, args.out_dir / f"{paper_id}.json", record))
    for paper_id, output_path, record in pending:
        output_path.write_text(json.dumps(record, indent=2))
        print(f"[assemble] {paper_id}: {sum(map(len, record['raw_by_role'].values()))} claims")


if __name__ == "__main__":
    main()