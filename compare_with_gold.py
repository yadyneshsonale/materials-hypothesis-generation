"""Compare our extracted (hypothesis_statement + causal_claim + mechanism_principle)
roles against each paper's own abstract, used here as a lightweight, always-available
gold-hypothesis proxy (see conversation: ResearchBench's audited main_hypothesis field
is the ideal gold, but its papers are mostly paywalled; the abstract is the same kind
of signal - the author's own explicit statement of the paper's main claim).

Scoring follows ACCELMAT's Closeness rubric: Concept Overlap, Property Overlap,
Keyword Matching, each 1-5, done by an LLM judge (no independent ground-truth
numeric answer key exists here, so this is a relative/consistency check, not an
absolute benchmark).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from llm_client import LLMError, chat_json

_JUDGE_SYSTEM = """You are scoring whether an AI system's extracted hypothesis (derived
independently from the paper's full text, WITHOUT ever seeing the abstract) matches the
paper's own abstract. Score three dimensions from 1-5 (5=excellent match):

- concept_overlap: do the core ideas/methods/materials align?
- property_overlap: do the claimed material properties/outcomes align (magnitude, direction)?
- keyword_matching: do specific entities (materials, mechanisms) match?

Return JSON: {"concept_overlap": 1-5, "property_overlap": 1-5, "keyword_matching": 1-5,
"justification": "<one sentence>"}"""


def load_extracted_claims(record_path: Path) -> str:
    d = json.loads(record_path.read_text())
    parts = []
    for role in ("hypothesis_statement", "causal_claim", "mechanism_principle"):
        items = d["reconciled_by_role"].get(role) or d["raw_by_role"].get(role, [])
        for it in items[:8]:  # cap to keep the judge prompt bounded
            parts.append(f"[{role}] {it.get('content', '')}")
    return "\n".join(parts) or "(nothing extracted for these roles)"


def judge_paper(paper_id: str, abstract: str, extracted_text: str, retries: int = 5) -> dict | None:
    user = f"ABSTRACT (gold):\n{abstract}\n\nEXTRACTED HYPOTHESIS-RELATED CONTENT (from our pipeline):\n{extracted_text}"
    for attempt in range(retries):
        try:
            return chat_json(_JUDGE_SYSTEM, user, max_tokens=600)
        except LLMError as e:
            wait = 2 ** attempt
            print(f"[compare] WARN: {paper_id} judge call failed (attempt {attempt + 1}/{retries}): {e} - retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    print(f"[compare] ERROR: {paper_id} judge call failed after {retries} attempts, skipping", file=sys.stderr)
    return None


def main() -> None:
    gold = json.loads(Path(sys.argv[1]).read_text())  # gold_abstracts.json
    outputs_dir = Path(sys.argv[2])  # outputs_real/
    results = {}
    for paper_id, meta in gold.items():
        record_path = outputs_dir / f"{paper_id}.json"
        if not record_path.exists():
            continue
        extracted_text = load_extracted_claims(record_path)
        score = judge_paper(paper_id, meta["abstract"], extracted_text)
        if score is None:
            continue
        results[paper_id] = {"title": meta["title"], **score}
        print(f"[compare] {paper_id}: {score}", file=sys.stderr)
    Path("gold_comparison.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
