"""Adaptive, traceable orchestration for materials hypothesis generation."""
from __future__ import annotations

import argparse
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from evidence_model import EvidenceRelation, index_relations, load_relations
from graph_build import Graph, Node, _keywords, build_graph
from hypothesis_agent import critique
from llm_client import provider_info, resilient_chat_json

MAX_DIRECT_HITS = 8
MAX_GRAPH_HITS = 8
MAX_PER_PAPER = 2
SUFFICIENCY_DECISIONS = {"sufficient", "reason_with_caveat", "decompose_further", "ask_user", "unresolved"}

_DECOMPOSE_SYSTEM = """You plan evidence gathering for materials hypothesis generation.
Convert the user's goal into a small directed acyclic graph of retrieval questions. Tasks must
cover mechanisms, interventions or transferable analogies, boundary conditions and failure modes,
and contradictory or comparative evidence. These are literature questions, not experiments to run.
Return JSON: {"tasks": [{"id": "T1", "question": "...", "intent": "...",
"depends_on": [], "required_roles": ["mechanism_principle"]}]}. Use only these role names:
problem_motivation, prior_approach, prior_limitation, rejected_alternative, inspiration_source,
causal_claim, mechanism_principle, hypothesis_statement, evidence_result, constraint, contradiction."""

_SUFFICIENCY_SYSTEM = """You assess whether retrieved literature claims answer one evidence task.
Keep retrieved facts separate from your inference. Return JSON with decision equal to one of:
sufficient, reason_with_caveat, decompose_further, ask_user, unresolved. Include a concise finding
grounded in cited entity IDs, a reason, missing_questions, and user_question. Use
decompose_further only when narrower literature questions can close the gap; ask_user only when a
missing preference or constraint would materially change the search.
Schema: {"decision": "...", "finding": "...", "cited_ids": ["..."], "reason": "...",
"missing_questions": ["..."], "user_question": "..."}."""

_ADJUDICATE_SYSTEM = """You adjudicate potentially conflicting materials-science claims without
choosing a winner from citation count or venue prestige. First test whether the claims differ in
material, composition, operating conditions, measurement protocol, scale, or model assumptions.
Weight directness, condition match, controls, uncertainty, sample size, replication, and method
quality. Return JSON: {"conflicts": [{"claim_ids": ["..."], "classification":
"direct_contradiction|different_regime|methodological_disagreement|different_property|insufficient_information",
"assessment": "...", "preferred_id": null, "reason": "..."}]}. Preserve both sides."""

_SYNTHESIZE_SYSTEM = """You generate auditable materials-science hypotheses from resolved evidence
tasks. Propose mechanism-specific candidates that combine claims from at least two papers. Every
literature-backed statement must cite a supplied entity ID; label any new connection as a proposed
inference. Include boundary conditions, predicted outcome, uncertainty, and a falsifying experiment.
Return JSON: {"candidates": [{"hypothesis": "...", "mechanism": "...", "predicted_outcome":
"...", "boundary_conditions": ["..."], "falsifying_experiment": "...", "uncertainties":
["..."], "cited_ids": ["..."], "proposed_inferences": ["..."]}]}."""


@dataclass
class Task:
    task_id: str
    question: str
    intent: str
    depends_on: list[str] = field(default_factory=list)
    required_roles: list[str] = field(default_factory=list)
    depth: int = 0
    status: str = "pending"
    finding: str = ""
    decision: str = ""
    cited_ids: list[str] = field(default_factory=list)


@dataclass
class EvidenceItem:
    node_id: str
    paper_id: str
    role: str
    content: str
    evidence_spans: list[str]
    score: float
    retrieval_reason: str


def _default_tasks(goal: str) -> list[Task]:
    return [
        Task("T1", f"Which mechanisms govern the target behavior in: {goal}?", "mechanisms", [], ["mechanism_principle", "causal_claim"]),
        Task("T2", f"Which interventions or cross-domain analogies could improve: {goal}?", "interventions", ["T1"], ["hypothesis_statement", "inspiration_source", "causal_claim"]),
        Task("T3", f"Under which conditions and failure modes do relevant approaches fail for: {goal}?", "boundaries", ["T1"], ["constraint", "prior_limitation", "rejected_alternative"]),
        Task("T4", f"Which findings compare or contradict candidate approaches for: {goal}?", "conflicts", ["T2", "T3"], ["contradiction", "evidence_result", "prior_approach"]),
    ]


def decompose_goal(goal: str) -> list[Task]:
    result = resilient_chat_json(_DECOMPOSE_SYSTEM, f"USER GOAL:\n{goal}", max_tokens=1800)
    rows = result.get("tasks", []) if isinstance(result, dict) else []
    tasks = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not row.get("question"):
            continue
        tasks.append(Task(
            task_id=str(row.get("id") or f"T{index + 1}"),
            question=str(row["question"]),
            intent=str(row.get("intent") or "evidence"),
            depends_on=[str(value) for value in row.get("depends_on", [])],
            required_roles=[str(value) for value in row.get("required_roles", [])],
        ))
    return tasks or _default_tasks(goal)


def retrieve_evidence(
    task: Task,
    graph: Graph,
    relation_index: dict[str, list[EvidenceRelation]] | None = None,
) -> list[EvidenceItem]:
    query_terms = _keywords(task.question)
    scored: list[tuple[float, Node]] = []
    for node in graph.nodes.values():
        overlap = len(query_terms & node.keywords)
        if not overlap:
            continue
        role_bonus = 1.5 if node.role in task.required_roles else 0.0
        scored.append((overlap + role_bonus, node))
    scored.sort(key=lambda value: (-value[0], value[1].node_id))

    selected: list[tuple[float, Node, str]] = []
    paper_counts: dict[str, int] = {}
    for score, node in scored:
        if paper_counts.get(node.paper_id, 0) >= MAX_PER_PAPER:
            continue
        selected.append((score, node, "lexical_role_seed"))
        paper_counts[node.paper_id] = paper_counts.get(node.paper_id, 0) + 1
        if len(selected) >= MAX_DIRECT_HITS:
            break

    seen = {node.node_id for _, node, _ in selected}
    expanded: list[tuple[float, Node, str]] = []
    for seed_score, seed, _ in selected:
        neighbors = sorted(graph.edges.get(seed.node_id, []), key=lambda value: (not value[2], -value[1]))
        for neighbor_id, weight, cross_paper in neighbors:
            if neighbor_id in seen:
                continue
            neighbor = graph.nodes[neighbor_id]
            seen.add(neighbor_id)
            relation = "cross_paper_graph_neighbor" if cross_paper else "same_paper_graph_neighbor"
            expanded.append((seed_score * weight, neighbor, f"{relation}:{seed.node_id}"))
            if len(expanded) >= MAX_GRAPH_HITS:
                break
        if len(expanded) >= MAX_GRAPH_HITS:
            break

    combined = selected + expanded
    if relation_index:
        for score, node, _ in selected:
            for relation in relation_index.get(node.node_id, []):
                linked_ids = [relation.source_entity_id, *relation.target_entity_ids]
                for linked_id in linked_ids:
                    if linked_id in seen or linked_id not in graph.nodes:
                        continue
                    seen.add(linked_id)
                    combined.append((
                        score * relation.confidence,
                        graph.nodes[linked_id],
                        f"typed_relation:{relation.relation_type}:{relation.relation_id}",
                    ))

    return [
        EvidenceItem(
            node_id=node.node_id,
            paper_id=node.paper_id,
            role=node.role,
            content=node.content,
            evidence_spans=node.evidence_spans,
            score=round(score, 4),
            retrieval_reason=reason,
        )
        for score, node, reason in combined
    ]


def assess_sufficiency(task: Task, evidence: list[EvidenceItem]) -> dict[str, Any]:
    evidence_block = "\n".join(
        f"- id={item.node_id} paper={item.paper_id} role={item.role}: {item.content}"
        for item in evidence
    ) or "(no evidence retrieved)"
    user = f"TASK:\n{task.question}\n\nEVIDENCE:\n{evidence_block}"
    result = resilient_chat_json(_SUFFICIENCY_SYSTEM, user, max_tokens=1200)
    if isinstance(result, dict) and result.get("decision") in SUFFICIENCY_DECISIONS:
        return result

    distinct_papers = {item.paper_id for item in evidence}
    decision = "reason_with_caveat" if len(evidence) >= 4 and len(distinct_papers) >= 2 else "unresolved"
    return {
        "decision": decision,
        "finding": f"Retrieved {len(evidence)} relevant entities from {len(distinct_papers)} papers; LLM synthesis was unavailable.",
        "cited_ids": [item.node_id for item in evidence[:6]],
        "reason": "Deterministic fallback based on evidence count and paper diversity.",
        "missing_questions": [],
        "user_question": "",
    }


def adjudicate_conflicts(goal: str, evidence: list[EvidenceItem]) -> dict[str, Any]:
    candidates = [item for item in evidence if item.role in {"contradiction", "rejected_alternative", "prior_limitation"}]
    if not candidates:
        return {"conflicts": []}
    block = "\n".join(f"- id={item.node_id} paper={item.paper_id}: {item.content}" for item in candidates)
    result = resilient_chat_json(_ADJUDICATE_SYSTEM, f"GOAL:\n{goal}\n\nCLAIMS:\n{block}", max_tokens=1400)
    return result if isinstance(result, dict) and isinstance(result.get("conflicts"), list) else {"conflicts": []}


def synthesize(goal: str, tasks: list[Task], evidence: list[EvidenceItem], conflicts: dict[str, Any]) -> list[dict[str, Any]]:
    findings = "\n".join(
        f"- {task.task_id} [{task.decision}]: {task.finding} (citations: {', '.join(task.cited_ids)})"
        for task in tasks if task.finding
    )
    evidence_block = "\n".join(
        f"- id={item.node_id} paper={item.paper_id} role={item.role}: {item.content}"
        for item in evidence
    )
    user = (
        f"GOAL:\n{goal}\n\nSUBTASK FINDINGS:\n{findings or '(none)'}\n\n"
        f"EVIDENCE ENTITIES:\n{evidence_block or '(none)'}\n\n"
        f"CONFLICT ASSESSMENT:\n{json.dumps(conflicts)}"
    )
    result = resilient_chat_json(_SYNTHESIZE_SYSTEM, user, max_tokens=3000)
    return result.get("candidates", []) if isinstance(result, dict) else []


def run_workflow(
    goal: str,
    outputs_dir: Path,
    trace_path: Path,
    max_depth: int = 1,
    relations_path: Path | None = None,
) -> dict[str, Any]:
    graph = build_graph(outputs_dir)
    relations = load_relations(relations_path)
    relation_index = index_relations(relations)
    tasks = decompose_goal(goal)
    trace: dict[str, Any] = {
        "run_id": str(uuid.uuid4()),
        "created_at": time.time(),
        "provider": provider_info(),
        "goal": goal,
        "graph": {
            "nodes": len(graph.nodes),
            "papers": len({node.paper_id for node in graph.nodes.values()}),
            "typed_relations": len(relations),
        },
        "events": [{"stage": "decompose", "tasks": [asdict(task) for task in tasks]}],
    }
    evidence_by_id: dict[str, EvidenceItem] = {}

    while any(task.status == "pending" for task in tasks):
        for task in tasks:
            dependency_states = {
                parent.status for parent in tasks
                if parent.task_id in task.depends_on
            }
            if task.status == "pending" and dependency_states & {"ask_user", "blocked_by_user"}:
                task.status = "blocked_by_user"
                task.decision = "ask_user"
                task.finding = "A dependency requires clarification from the user."
        ready = [
            task for task in tasks if task.status == "pending"
            and all(next((parent.status for parent in tasks if parent.task_id == dep), "unresolved") != "pending" for dep in task.depends_on)
        ]
        if not ready:
            for task in tasks:
                if task.status == "pending":
                    task.status = "unresolved"
                    task.decision = "unresolved"
                    task.finding = "Task dependencies could not be resolved."
            break

        for task in ready:
            evidence = retrieve_evidence(task, graph, relation_index)
            for item in evidence:
                evidence_by_id[item.node_id] = item
            assessment = assess_sufficiency(task, evidence)
            task.decision = str(assessment.get("decision", "unresolved"))
            task.finding = str(assessment.get("finding", ""))
            task.cited_ids = [str(value) for value in assessment.get("cited_ids", []) if str(value) in evidence_by_id]
            task.status = "complete" if task.decision in {"sufficient", "reason_with_caveat"} else task.decision

            children: list[Task] = []
            if task.decision == "decompose_further" and task.depth < max_depth:
                for index, question in enumerate(assessment.get("missing_questions", []), start=1):
                    child_id = f"{task.task_id}.{index}"
                    children.append(Task(child_id, str(question), "gap_closure", task.depends_on.copy(), task.required_roles.copy(), task.depth + 1))
                tasks.extend(children)
                task.status = "decomposed"

            trace["events"].append({
                "stage": "subtask",
                "task_id": task.task_id,
                "question": task.question,
                "retrieved": [asdict(item) for item in evidence],
                "assessment": assessment,
                "children": [asdict(child) for child in children],
            })

    needs_user = any(task.status == "ask_user" for task in tasks)
    all_evidence = list(evidence_by_id.values())
    conflicts = adjudicate_conflicts(goal, all_evidence)
    candidates = [] if needs_user else synthesize(goal, tasks, all_evidence, conflicts)
    valid_ids = set(evidence_by_id)
    candidate_records = []
    for candidate in candidates:
        cited_ids = [str(value) for value in candidate.get("cited_ids", []) if str(value) in valid_ids]
        candidate["cited_ids"] = cited_ids
        candidate["critics"] = critique(goal, candidate)
        candidate_records.append(candidate)

    trace.update({
        "tasks": [asdict(task) for task in tasks],
        "conflicts": conflicts,
        "candidates": candidate_records,
        "status": "needs_user" if needs_user else ("complete" if candidate_records else "complete_without_candidates"),
    })
    final_stage = "await_user" if needs_user else "synthesis"
    trace["events"].append({"stage": final_stage, "candidate_count": len(candidate_records)})
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(json.dumps(trace, indent=2))
    return trace


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("goal")
    parser.add_argument("outputs_dir", type=Path)
    parser.add_argument("trace_path", type=Path)
    parser.add_argument("--max-depth", type=int, default=1)
    parser.add_argument("--relations", type=Path, help="optional JSONL file of typed evidence relations")
    args = parser.parse_args()
    result = run_workflow(args.goal, args.outputs_dir, args.trace_path, args.max_depth, args.relations)
    print(f"[adaptive] status={result['status']} tasks={len(result['tasks'])} candidates={len(result['candidates'])}")
    print(f"[adaptive] trace={args.trace_path}")


if __name__ == "__main__":
    main()