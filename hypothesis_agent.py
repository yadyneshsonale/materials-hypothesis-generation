"""Hypothesis Generation Agent (MatHG Stage 3-6), built on the Stage-1 extraction
outputs via the cross-paper graph in graph_build.py.

Pipeline per goal: retrieve (non-linear, cross-paper-biased) -> compose (multiple,
principle-constrained candidates) -> critique (multi-persona) -> registry (HEP-style
provenance + lifecycle). See graph_build.py's docstring for why retrieval is flattened
across papers/roles instead of following any paper's own argument order.
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from graph_build import Graph, Node, _keywords, build_graph
from llm_client import LLMError, chat_json, resilient_chat_json

TOP_DIRECT_HITS = 6
MAX_PER_PAPER_DIRECT = 2
NEIGHBOR_EXPANSION = 10
N_CANDIDATES = 3
BEAM_WIDTH = 2
MAX_ROUNDS = 2


# ---------- Stage 3: retrieval (non-linear, cross-paper-biased) ----------

def retrieve(goal: str, g: Graph, top_direct: int = TOP_DIRECT_HITS) -> list[Node]:
    goal_kw = _keywords(goal)
    scored = []
    for node in g.nodes.values():
        overlap = len(goal_kw & node.keywords)
        if overlap:
            scored.append((overlap, node))
    scored.sort(key=lambda x: -x[0])

    direct: list[Node] = []
    per_paper_count: dict[str, int] = {}
    for _, node in scored:
        if per_paper_count.get(node.paper_id, 0) >= MAX_PER_PAPER_DIRECT:
            continue
        direct.append(node)
        per_paper_count[node.paper_id] = per_paper_count.get(node.paper_id, 0) + 1
        if len(direct) >= top_direct:
            break

    # Expand 1-hop, explicitly preferring cross-paper edges - this is the "non-linear"
    # move: pull in items that never co-occurred with the direct hits in any one paper.
    seen = {n.node_id for n in direct}
    expanded: list[Node] = []
    for node in direct:
        neighbors = g.edges.get(node.node_id, [])
        cross = [n for n in neighbors if n[2]]
        same = [n for n in neighbors if not n[2]]
        for (nbr_id, _, _) in (cross + same):
            if nbr_id in seen:
                continue
            seen.add(nbr_id)
            expanded.append(g.nodes[nbr_id])
            if len(expanded) >= NEIGHBOR_EXPANSION:
                break
    return direct + expanded


# ---------- Stage 4: composition (principle-constrained, multiple candidates) ----------

_COMPOSE_SYSTEM = """You are a Hypothesis Agent for materials-science research. You are given a
research goal and a pool of inspiration items pulled from several DIFFERENT, otherwise unrelated
papers (tagged with paper_id and role). Some items come from the same paper as each other; many
were deliberately pulled from different papers because they share an underlying theme even though
they discuss different material systems.

Your job: propose new hypotheses that COMBINE items from at least two different papers into one
mechanistically-grounded claim. Do not just restate one paper's own hypothesis. Every hypothesis
must:
1. name a specific proposed mechanism/principle (not just "X might help with Y")
2. explicitly cite which inspiration items (by their id) it combines
3. state why this combination is non-obvious (what field/system boundary it crosses)

Return JSON: {"candidates": [{"hypothesis": "...", "mechanism": "...", "cited_ids": ["..."],
"crosses_boundary": "..."}]} with exactly N candidates."""


def compose(goal: str, inspirations: list[Node], n: int = N_CANDIDATES) -> list[dict]:
    items_block = "\n".join(
        f"- id={n.node_id} paper={n.paper_id} role={n.role}: {n.content}" for n in inspirations
    )
    user = f"RESEARCH GOAL:\n{goal}\n\nINSPIRATION POOL:\n{items_block}\n\nPropose {n} candidates."
    result = resilient_chat_json(_COMPOSE_SYSTEM.replace("N ", f"{n} "), user, max_tokens=3000)
    return result.get("candidates", []) if isinstance(result, dict) else []


# ---------- Stage 5: critique (multi-persona, ACCELMAT-style) ----------

_CRITIC_PERSONAS = {
    "plausibility_critic": "You are a skeptical domain expert. Score whether this hypothesis is physically/chemically plausible given established principles.",
    "novelty_critic": "You are evaluating novelty. Score whether this hypothesis is a genuinely non-obvious cross-domain combination, versus a trivial restatement of one paper's own claim.",
    "feasibility_critic": "You are an experimentalist. Score whether this hypothesis could realistically be tested with standard materials-characterization techniques.",
}

_CRITIC_SYSTEM = """{persona}

Score the hypothesis 1-5 (5=best) and give one sentence of feedback.
Return JSON: {{"score": 1-5, "feedback": "..."}}"""


def critique(goal: str, candidate: dict) -> dict:
    scores = {}
    for name, persona in _CRITIC_PERSONAS.items():
        user = f"GOAL: {goal}\n\nHYPOTHESIS: {candidate.get('hypothesis')}\nMECHANISM: {candidate.get('mechanism')}"
        result = resilient_chat_json(_CRITIC_SYSTEM.format(persona=persona), user, max_tokens=300)
        scores[name] = result if result is not None else {"score": None, "feedback": "critic call failed after retries"}
    return scores


def _avg_score(critic_scores: dict) -> float | None:
    vals = [v.get("score") for v in critic_scores.values() if isinstance(v.get("score"), (int, float))]
    return sum(vals) / len(vals) if vals else None


# ---------- Stage 4b: branching - refine (ACCELMAT-style revision) and merge (HEP's 4th mechanism) ----------

_REFINE_SYSTEM = """You are revising ONE hypothesis in response to specific critic feedback. Keep
what's working; directly address the weakest-scoring critique below. Do not soften the claim into
something vague just to avoid criticism - propose a genuinely more plausible/novel/testable variant.

You may re-cite the same inspiration item ids already used by the original hypothesis; do not invent
new ids you were not given.

Return a single JSON object (not a list): {"hypothesis": "...", "mechanism": "...",
"cited_ids": ["..."], "crosses_boundary": "..."}"""

_MERGE_SYSTEM = """You are given TWO surviving hypotheses from independent branches of a search.
Propose ONE new hypothesis that combines the strongest, most complementary elements of both -
not a superficial concatenation, but a genuine synthesis where the mechanisms reinforce each other.

You may re-cite ids already used by either parent; do not invent new ids you were not given.

Return a single JSON object (not a list): {"hypothesis": "...", "mechanism": "...",
"cited_ids": ["..."], "crosses_boundary": "..."}"""


def refine(goal: str, record: "HypothesisRecord") -> dict | None:
    feedback = "\n".join(f"- {k}: score={v.get('score')} - {v.get('feedback')}" for k, v in record.critic_scores.items())
    cited = "\n".join(f"  id={n['node_id']}: {n['content']}" for n in record.cited_nodes)
    user = (
        f"GOAL: {goal}\n\nORIGINAL HYPOTHESIS: {record.hypothesis}\nORIGINAL MECHANISM: {record.mechanism}\n\n"
        f"CITED ITEMS:\n{cited}\n\nCRITIC FEEDBACK:\n{feedback}"
    )
    return resilient_chat_json(_REFINE_SYSTEM, user, max_tokens=1200)


def merge(goal: str, record_a: "HypothesisRecord", record_b: "HypothesisRecord") -> dict | None:
    def _block(r: "HypothesisRecord") -> str:
        cited = "\n".join(f"  id={n['node_id']}: {n['content']}" for n in r.cited_nodes)
        return f"Hypothesis: {r.hypothesis}\nMechanism: {r.mechanism}\nCited items:\n{cited}"
    user = f"GOAL: {goal}\n\nBRANCH A:\n{_block(record_a)}\n\nBRANCH B:\n{_block(record_b)}"
    return resilient_chat_json(_MERGE_SYSTEM, user, max_tokens=1200)


# ---------- Stage 6: registry (HEP-style provenance + lifecycle) ----------

@dataclass
class HypothesisRecord:
    hypothesis_id: str
    goal: str
    hypothesis: str
    mechanism: str
    crosses_boundary: str
    cited_nodes: list[dict]
    critic_scores: dict
    lifecycle_state: str
    parent_ids: list[str] = field(default_factory=list)
    generation_mechanism: str = "de_novo"  # de_novo | refine | merge (HEP's generation mechanisms)
    round_num: int = 0
    created_at: float = field(default_factory=time.time)


def _resolve_cited_nodes(candidate: dict, g: Graph) -> list[dict]:
    out = []
    for nid in candidate.get("cited_ids", []):
        node = g.nodes.get(nid)
        if node:
            out.append({"node_id": nid, "paper_id": node.paper_id, "role": node.role, "content": node.content})
    return out


def _lifecycle_state(critic_scores: dict) -> str:
    vals = [v.get("score") for v in critic_scores.values() if isinstance(v.get("score"), (int, float))]
    if not vals:
        return "proposed"
    avg = sum(vals) / len(vals)
    if avg >= 4:
        return "supported"
    if avg <= 2:
        return "refuted"
    return "under_test"


def run_agent(goal: str, outputs_dir: Path, registry_path: Path) -> list[HypothesisRecord]:
    """One-shot: compose N candidates, critique once, no branching. Kept as the simple baseline."""
    g = build_graph(outputs_dir)
    inspirations = retrieve(goal, g)
    print(f"[agent] retrieved {len(inspirations)} inspiration nodes "
          f"({len({n.paper_id for n in inspirations})} distinct papers)", file=sys.stderr)

    candidates = compose(goal, inspirations)
    print(f"[agent] composed {len(candidates)} candidate hypotheses", file=sys.stderr)

    records = []
    for cand in candidates:
        scores = critique(goal, cand)
        record = HypothesisRecord(
            hypothesis_id=str(uuid.uuid4())[:8],
            goal=goal,
            hypothesis=cand.get("hypothesis", ""),
            mechanism=cand.get("mechanism", ""),
            crosses_boundary=cand.get("crosses_boundary", ""),
            cited_nodes=_resolve_cited_nodes(cand, g),
            critic_scores=scores,
            lifecycle_state=_lifecycle_state(scores),
        )
        records.append(record)
        print(f"[agent] {record.hypothesis_id}: {record.lifecycle_state} - {record.hypothesis[:100]}", file=sys.stderr)

    existing = json.loads(registry_path.read_text()) if registry_path.exists() else []
    existing.extend(asdict(r) for r in records)
    registry_path.write_text(json.dumps(existing, indent=2))
    return records


def run_agent_search(
    goal: str, outputs_dir: Path, registry_path: Path,
    max_rounds: int = MAX_ROUNDS, beam_width: int = BEAM_WIDTH, n_initial: int = N_CANDIDATES,
) -> list[HypothesisRecord]:
    """Beam-search over hypothesis space: de-novo compose -> critique -> repeatedly keep the
    top-`beam_width` survivors, branch each via refine, branch each surviving pair via merge,
    critique the new branches, and stop early once a round fails to beat the previous best."""
    g = build_graph(outputs_dir)
    inspirations = retrieve(goal, g)
    print(f"[agent] retrieved {len(inspirations)} inspiration nodes "
          f"({len({n.paper_id for n in inspirations})} distinct papers)", file=sys.stderr)

    all_records: list[HypothesisRecord] = []

    def make_record(cand: dict, parent_ids: list[str], mechanism: str, round_num: int) -> HypothesisRecord:
        scores = critique(goal, cand)
        rec = HypothesisRecord(
            hypothesis_id=str(uuid.uuid4())[:8],
            goal=goal,
            hypothesis=cand.get("hypothesis", ""),
            mechanism=cand.get("mechanism", ""),
            crosses_boundary=cand.get("crosses_boundary", ""),
            cited_nodes=_resolve_cited_nodes(cand, g),
            critic_scores=scores,
            lifecycle_state=_lifecycle_state(scores),
            parent_ids=parent_ids,
            generation_mechanism=mechanism,
            round_num=round_num,
        )
        all_records.append(rec)
        avg = _avg_score(scores)
        avg_s = f"{avg:.1f}" if avg is not None else "n/a"
        print(f"[agent] round {round_num} [{mechanism}] {rec.hypothesis_id} avg={avg_s} "
              f"{rec.lifecycle_state} - {rec.hypothesis[:90]}", file=sys.stderr)
        return rec

    candidates = compose(goal, inspirations, n=n_initial)
    print(f"[agent] round 0: composed {len(candidates)} de-novo candidates", file=sys.stderr)
    survivors = [make_record(c, [], "de_novo", 0) for c in candidates]

    best_avg = max((_avg_score(r.critic_scores) or 0) for r in survivors) if survivors else 0
    for round_num in range(1, max_rounds + 1):
        survivors.sort(key=lambda r: -(_avg_score(r.critic_scores) or 0))
        top = survivors[:beam_width]

        new_records: list[HypothesisRecord] = []
        for r in top:
            variant = refine(goal, r)
            if variant:
                new_records.append(make_record(variant, [r.hypothesis_id], "refine", round_num))
        for i in range(len(top)):
            for j in range(i + 1, len(top)):
                variant = merge(goal, top[i], top[j])
                if variant:
                    new_records.append(make_record(variant, [top[i].hypothesis_id, top[j].hypothesis_id], "merge", round_num))

        if not new_records:
            print(f"[agent] round {round_num}: no new branches produced, stopping", file=sys.stderr)
            break

        candidate_pool = top + new_records
        new_best = max((_avg_score(r.critic_scores) or 0) for r in candidate_pool)
        survivors = candidate_pool
        if new_best <= best_avg:
            print(f"[agent] round {round_num}: no improvement over best={best_avg:.1f}, stopping early", file=sys.stderr)
            break
        best_avg = new_best

    survivors.sort(key=lambda r: -(_avg_score(r.critic_scores) or 0))
    best = survivors[0]
    best.lifecycle_state = "promoted_best"
    print(f"[agent] FINAL BEST ({best.generation_mechanism}, round {best.round_num}): "
          f"{best.hypothesis_id} avg={_avg_score(best.critic_scores):.1f} - {best.hypothesis}", file=sys.stderr)

    existing = json.loads(registry_path.read_text()) if registry_path.exists() else []
    existing.extend(asdict(r) for r in all_records)
    registry_path.write_text(json.dumps(existing, indent=2))
    return all_records


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("goal")
    ap.add_argument("outputs_dir", type=Path)
    ap.add_argument("registry_path", type=Path, nargs="?", default=Path("registry.json"))
    ap.add_argument("--search", action="store_true", help="use beam-search branching instead of one-shot")
    ap.add_argument("--rounds", type=int, default=MAX_ROUNDS)
    ap.add_argument("--beam", type=int, default=BEAM_WIDTH)
    args = ap.parse_args()

    if args.search:
        run_agent_search(args.goal, args.outputs_dir, args.registry_path, max_rounds=args.rounds, beam_width=args.beam)
    else:
        run_agent(args.goal, args.outputs_dir, args.registry_path)
