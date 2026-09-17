"""Audit extraction outputs against source text: (1) grounding - does every
evidence_span actually appear in the paper (exact or near-exact), (2) coverage -
are there obvious trigger-phrase sentences in the source that never made it
into any extracted item for the relevant role.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path

TRIGGER_PATTERNS = {
    "rejected_alternative": [r"\brather than\b", r"\bunlike\b", r"\binstead of\b", r"\bwe did not\b", r"\bwe avoid"],
    "prior_limitation": [r"\bhowever,?\s+(this|these|it|they)\b", r"\bfails? to\b", r"\blimited by\b", r"\bdoes not (account|capture)\b"],
    "contradiction": [r"\bin contrast\b", r"\bunexpectedly\b", r"\bcontrary to\b", r"\bdisagrees? with\b"],
}

FUZZY_RATIO_THRESHOLD = 0.6


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _alnum_only(s: str) -> str:
    """Strip everything but letters/digits. Collapses whitespace, hyphenated line-wraps
    ("cre-\\nate" -> "create"), and page-break mid-sentence splits into one contiguous
    string, so exact-substring matching survives common PDF-to-text reflow artifacts
    without falsely flagging them as hallucinated evidence."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _fuzzy_ratio(span: str, source: str) -> float:
    """Best-effort fuzzy match: anchor on the span's longest word, scan its occurrences
    in the source, and take the max SequenceMatcher ratio over a window around each."""
    words = sorted(re.findall(r"[a-zA-Z]{6,}", span), key=len, reverse=True)
    if not words:
        return 0.0
    anchor = words[0].lower()
    src_lower = source.lower()
    best = 0.0
    win = max(len(span) * 2, 100)
    start = 0
    while True:
        pos = src_lower.find(anchor, start)
        if pos == -1:
            break
        lo = max(0, pos - win // 2)
        hi = min(len(source), pos + win // 2)
        ratio = difflib.SequenceMatcher(None, span.lower(), source[lo:hi].lower()).ratio()
        best = max(best, ratio)
        start = pos + 1
    return best


def check_grounding(record: dict, source_text: str) -> tuple[list[str], list[str]]:
    """Returns (hard_problems, fuzzy_notes). Hard problems are spans found neither
    exactly (whitespace/hyphenation-normalized) nor within FUZZY_RATIO_THRESHOLD of
    any window of the source - the closest thing to a real hallucination signal this
    script can give without a proper aligner."""
    alnum_source = _alnum_only(source_text)
    problems, fuzzy_notes = [], []
    for role, items in record["reconciled_by_role"].items():
        for it in items:
            for span in it.get("evidence_spans", []):
                if _alnum_only(span) in alnum_source:
                    continue  # exact modulo whitespace/hyphenation - fine
                ratio = _fuzzy_ratio(span, source_text)
                if ratio >= FUZZY_RATIO_THRESHOLD:
                    fuzzy_notes.append(f"  [{role}] fuzzy match (ratio={ratio:.2f}): \"{span[:100]}\"")
                else:
                    problems.append(f"  [{role}] NOT grounded (best fuzzy ratio={ratio:.2f}): \"{span[:100]}\"")
    return problems, fuzzy_notes


def check_coverage(source_text: str) -> dict[str, list[str]]:
    sentences = re.split(r"(?<=[.!?])\s+", source_text)
    hits = {role: [] for role in TRIGGER_PATTERNS}
    for role, patterns in TRIGGER_PATTERNS.items():
        for sent in sentences:
            s = sent.strip()
            if len(s) < 20 or len(s) > 400:
                continue
            if any(re.search(p, s, re.IGNORECASE) for p in patterns):
                hits[role].append(s)
    return hits


def main() -> None:
    outputs_dir = Path(sys.argv[1])
    texts_dir = Path(sys.argv[2])
    for record_path in sorted(outputs_dir.glob("*.json")):
        paper_id = record_path.stem
        record = json.loads(record_path.read_text())
        source_text = (texts_dir / f"{paper_id}.txt").read_text(encoding="utf-8", errors="ignore")

        print(f"\n{'='*90}\n{paper_id}\n{'='*90}")

        problems, fuzzy_notes = check_grounding(record, source_text)
        if problems:
            print(f"GROUNDING ISSUES ({len(problems)}) - likely real, not just reflow noise:")
            for p in problems[:10]:
                print(p)
        else:
            print("GROUNDING: no hard failures.")
        if fuzzy_notes:
            print(f"  ({len(fuzzy_notes)} fuzzy-matched spans, treated as OK - PDF reflow, not hallucination)")

        candidate_hits = check_coverage(source_text)
        for role, sentences in candidate_hits.items():
            extracted_n = len(record["reconciled_by_role"].get(role, []))
            print(f"COVERAGE [{role}]: {len(sentences)} trigger-phrase sentence(s) in source vs {extracted_n} extracted")
            for s in sentences[:5]:
                print(f"    candidate: {s[:160]}")


if __name__ == "__main__":
    main()
