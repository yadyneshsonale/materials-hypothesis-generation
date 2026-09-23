"""Stage 1 orchestration: chunk -> per-chunk role extraction -> aggregate -> reconcile."""
from __future__ import annotations

from dataclasses import dataclass, field

from chunking import Chunk, split_into_chunks
from llm_client import LLMError, TruncatedError, chat_json
from roles import ROLE_KEYS, role_table_prompt

DIGEST_MAX_ITEMS = 25
DIGEST_ITEM_CHARS = 160
MAX_SPLIT_DEPTH = 3

_EXTRACT_SYSTEM = """You extract argumentative content from one section of a materials-science paper.

You are given a fixed set of roles. For this chunk of text, find every span that matches
ANY of the roles below (a chunk may contain zero, one, or several matches per role; most
roles will have zero matches in most chunks, that's expected).

ROLES:
{roles}

Return a JSON object: {{"items": [{{"role": "<role_key>", "content": "<concise paraphrase>",
"evidence_span": "<verbatim quote from the text>"}}, ...]}}. Only use role_key values from the
list above. If nothing matches, return {{"items": []}}."""

_SECTION_GUIDANCE = """Apply section-aware emphasis without imposing quotas:
- Introduction/background: problem_motivation, prior_approach, prior_limitation, inspiration_source.
- Methods: rejected_alternative and genuine experimental/design constraints.
- Results: measured evidence_result and directly supported causal_claim.
- Discussion/conclusion: mechanism_principle, hypothesis_statement, and explicit contradiction.
Extract every high-signal match. Do not fill a role merely to make it non-empty. Keep observations,
mechanisms, hypotheses, constraints, and contradictions distinct according to their definitions."""

_RECONCILE_SYSTEM = """You reconcile candidate extractions for ONE role, gathered independently
from every section of a paper. Merge near-duplicate mentions, and where two items are clearly
two halves of the same underlying claim split across sections (e.g. a cause stated in one
section and its effect in another), stitch them into one combined item. If items genuinely
conflict (e.g. two different hypothesis statements that disagree), keep both and set
"conflicting": true. Return JSON: {"items": [{"content": "...", "evidence_spans": ["...", ...],
"conflicting": false}, ...]}"""


@dataclass
class PaperRecord:
    paper_id: str
    raw_by_role: dict[str, list[dict]] = field(default_factory=lambda: {k: [] for k in ROLE_KEYS})
    reconciled_by_role: dict[str, list[dict]] = field(default_factory=dict)
    chunks_processed: int = 0


def _digest_line(item: dict) -> str:
    content = item.get("content", "")[:DIGEST_ITEM_CHARS]
    return f"[{item.get('role')}] {content}"


def _extract_text(section: str, text: str, digest: list[str], depth: int = 0) -> list[dict]:
    digest_block = "\n".join(digest[-DIGEST_MAX_ITEMS:]) or "(none yet)"
    user = (
        f"Context extracted so far (for resolving references like 'the method described above'):\n"
        f"{digest_block}\n\n"
        f"{_SECTION_GUIDANCE}\n\n"
        f"--- SECTION: {section} ---\n{text}"
    )
    try:
        result = chat_json(_EXTRACT_SYSTEM.format(roles=role_table_prompt()), user, max_tokens=8000)
    except TruncatedError as e:
        lines = text.splitlines()
        if depth >= MAX_SPLIT_DEPTH or len(lines) < 4:
            print(f"[mathg] WARN: {section} still truncated after {depth} splits, giving up: {e}")
            return []
        print(f"[mathg] INFO: {section} response truncated, splitting chunk in half and retrying (depth={depth + 1})")
        mid = len(lines) // 2
        first_half = "\n".join(lines[:mid])
        second_half = "\n".join(lines[mid:])
        return (
            _extract_text(f"{section}/a", first_half, digest, depth + 1)
            + _extract_text(f"{section}/b", second_half, digest, depth + 1)
        )
    except LLMError:
        raise
    except Exception as e:  # noqa: BLE001 - a single bad chunk must not kill the whole paper
        print(f"[mathg] WARN: {section} extraction failed, skipping: {e}")
        return []
    items = result.get("items", []) if isinstance(result, dict) else []
    return [it for it in items if it.get("role") in ROLE_KEYS]


def extract_chunk(chunk: Chunk, digest: list[str]) -> list[dict]:
    return _extract_text(chunk.section, chunk.text, digest)


def reconcile_role(role: str, items: list[dict]) -> list[dict]:
    if not items:
        return []
    listing = "\n".join(f"- {it.get('content', '')} (evidence: {it.get('evidence_span', '')})" for it in items)
    user = f"Role: {role}\n\nCandidate items from across the paper's sections:\n{listing}"
    try:
        result = chat_json(_RECONCILE_SYSTEM, user, max_tokens=8000)
    except LLMError:
        raise
    except Exception as e:  # noqa: BLE001 - reconciliation failure shouldn't drop the raw items already found
        print(f"[mathg] WARN: reconciliation failed for role={role}, keeping raw items unreconciled: {e}")
        return items
    return result.get("items", []) if isinstance(result, dict) else []


def extract_paper(paper_id: str, full_text: str) -> PaperRecord:
    record = PaperRecord(paper_id=paper_id)
    digest: list[str] = []
    for chunk in split_into_chunks(full_text):
        items = extract_chunk(chunk, digest)
        for item in items:
            record.raw_by_role[item["role"]].append(item)
            digest.append(_digest_line(item))
        record.chunks_processed += 1
    for role, items in record.raw_by_role.items():
        record.reconciled_by_role[role] = reconcile_role(role, items)
    return record


def record_to_dict(record: PaperRecord) -> dict:
    return {
        "paper_id": record.paper_id,
        "chunks_processed": record.chunks_processed,
        "raw_by_role": record.raw_by_role,
        "reconciled_by_role": record.reconciled_by_role,
    }
