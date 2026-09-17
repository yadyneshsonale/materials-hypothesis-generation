"""Split a paper into chunks for role extraction.

Prefers real section headers when detectable; falls back to fixed-size
paragraph windows for papers with irregular structure. Either way, every
chunk is later checked against *every* role (Stage 1's whole point is to
not assume where a role's content lives).

After the initial split, every chunk is checked against a token budget
(60% of the model's context window, leaving room for the system prompt,
role table, and rolling digest). Oversized chunks are split further: by
detected subsection headers (e.g. "3.1 Synthesis") if present, otherwise
by lines with overlap.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from llm_client import context_window_tokens, estimate_tokens

_HEADER_RE = re.compile(
    r"^\s*(?:\d+[\.\)]?\s*)?"
    r"(abstract|introduction|background|related work|literature review|"
    r"materials?(?:\s+and\s+methods?)?|methods?|experimental(?:\s+section)?|"
    r"results?(?:\s+and\s+discussion)?|discussion|conclusion|"
    r"acknowledg(?:e)?ments?|references|supporting information)\s*$",
    re.IGNORECASE,
)

_SUBHEADER_RE = re.compile(r"^\s*\d+\.\d+[\.\)]?\s+\S")

WORDS_PER_CHUNK = 900
WORDS_OVERLAP = 100

CHUNK_BUDGET_FRACTION = 0.6


def _chunk_token_budget() -> int:
    return int(context_window_tokens() * CHUNK_BUDGET_FRACTION)


@dataclass
class Chunk:
    section: str
    text: str
    index: int


def _split_by_headers(text: str) -> list[tuple[str, str]] | None:
    lines = text.splitlines()
    boundaries = [(i, m.group(1).title()) for i, ln in enumerate(lines) if (m := _HEADER_RE.match(ln))]
    if len(boundaries) < 2:
        return None  # not enough structure to trust header-based splitting
    parts = []
    for idx, (start, name) in enumerate(boundaries):
        end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(lines)
        body = "\n".join(lines[start + 1:end]).strip()
        if body:
            parts.append((name, body))
    return parts or None


def _split_by_subheaders(text: str) -> list[str] | None:
    lines = text.splitlines()
    boundaries = [i for i, ln in enumerate(lines) if _SUBHEADER_RE.match(ln)]
    if len(boundaries) < 2:
        return None
    parts = []
    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        if body:
            parts.append(body)
    return parts or None


def _split_lines_with_overlap(text: str, token_budget: int) -> list[str]:
    lines = text.splitlines() or [text]
    total_tokens = estimate_tokens(text) or 1
    tokens_per_line = max(total_tokens / len(lines), 1)
    lines_per_chunk = max(int(token_budget / tokens_per_line), 1)
    overlap_lines = max(lines_per_chunk // 10, 1)
    parts = []
    start = 0
    while start < len(lines):
        end = min(start + lines_per_chunk, len(lines))
        parts.append("\n".join(lines[start:end]))
        if end == len(lines):
            break
        start = end - overlap_lines
    return parts


def _ensure_within_budget(section: str, text: str) -> list[tuple[str, str]]:
    """Recursively split (section_name, text) until every piece fits the token budget."""
    budget = _chunk_token_budget()
    if estimate_tokens(text) <= budget:
        return [(section, text)]

    sub_parts = _split_by_subheaders(text)
    if sub_parts:
        out = []
        for i, part in enumerate(sub_parts):
            out.extend(_ensure_within_budget(f"{section}.{i + 1}", part))
        return out

    # no subsection structure found - fall back to line-based windowing with overlap
    out = []
    for i, part in enumerate(_split_lines_with_overlap(text, budget)):
        # a line-window can still theoretically exceed budget if a single line is huge
        # (e.g. a giant table row); recurse once more defensively, but don't loop forever.
        if estimate_tokens(part) > budget and part != text:
            out.extend(_ensure_within_budget(f"{section}~{i + 1}", part))
        else:
            out.append((f"{section}~{i + 1}", part))
    return out


def split_into_chunks(text: str) -> list[Chunk]:
    header_parts = _split_by_headers(text)
    if header_parts is None:
        idx = 0
        fixed_parts = []
        words = text.split()
        start = 0
        while start < len(words):
            end = min(start + WORDS_PER_CHUNK, len(words))
            fixed_parts.append((f"window_{idx}", " ".join(words[start:end])))
            if end == len(words):
                break
            start = end - WORDS_OVERLAP
            idx += 1
        header_parts = fixed_parts

    budgeted: list[tuple[str, str]] = []
    for name, body in header_parts:
        budgeted.extend(_ensure_within_budget(name, body))

    return [Chunk(section=name, text=body, index=i) for i, (name, body) in enumerate(budgeted)]
