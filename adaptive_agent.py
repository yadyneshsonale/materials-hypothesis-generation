"""Adaptive, traceable orchestration for materials hypothesis generation."""
from __future__ import annotations

import argparse
import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from evidence_model import EvidenceEntity, EvidenceRelation, index_relations, load_entities, load_relations
from graph_build import Graph, Node, _keywords, build_graph
from hypothesis_agent import critique
from llm_client import provider_info, resilient_chat_json
from materials_evidence import MaterialsEvidenceUnit, load_materials_evidence
from source_context import load_context_index

MAX_DIRECT_HITS = 8
MAX_GRAPH_HITS = 8
MAX_PER_PAPER = 2
MAX_CITATION_HITS = 8
MAX_SYNTHESIS_EVIDENCE = 20
SUFFICIENCY_DECISIONS = {"sufficient", "reason_with_caveat", "decompose_further", "unresolved"}


def _context_keywords(text: str) -> set[str]:
    terms = set()
    for term in re.findall(r"[a-z][a-z0-9-]{2,}", text.lower()):
        if term.startswith("compar"):
            term = "compare"
        elif term.endswith("s") and len(term) > 4:
            term = term[:-1]
        terms.add(term)
    return terms

_SUFFICIENCY_SYSTEM = """You assess whether retrieved literature claims answer one evidence task.
Prefer complete linked materials evidence that retains composition, processing, structure,
mechanism, property outcome, conditions, comparison, and provenance. Do not join fields from
different material states or operating regimes. Keep retrieved facts separate from your inference.
Return JSON with decision equal to one of:
sufficient, reason_with_caveat, decompose_further, unresolved. Include a concise finding grounded
in cited entity IDs, a reason, missing_questions, and assumptions. Use decompose_further only when
narrower literature questions can close the gap. When a preference or constraint is absent, choose
a conservative default, record it in assumptions, and continue with reason_with_caveat.
Bibliography metadata and citations marked METADATA_ONLY or REQUIRES_RESOLUTION are routing
information, not substantive evidence from the cited paper. Do not infer the cited paper's methods,
conditions, or results from its title. Treat low-confidence raw table text as provisional.
Schema: {"decision": "...", "finding": "...", "cited_ids": ["..."], "reason": "...",
"missing_questions": ["..."], "assumptions": ["..."]}."""

_ADJUDICATE_SYSTEM = """You adjudicate potentially conflicting materials-science claims without
choosing a winner from citation count or venue prestige. First test whether the claims differ in
material, composition, operating conditions, measurement protocol, scale, or model assumptions.
Weight directness, condition match, controls, uncertainty, sample size, replication, and method
quality. Bibliography metadata is not evidence about a cited paper's methods or results. Return
JSON: {"conflicts": [{"claim_ids": ["..."], "classification":
"direct_contradiction|different_regime|methodological_disagreement|different_property|insufficient_information",
"assessment": "...", "preferred_id": null, "reason": "..."}]}. Preserve both sides."""

_SYNTHESIZE_SYSTEM = """You generate auditable materials-science hypotheses from resolved evidence
tasks. Propose mechanism-specific candidates that combine claims from at least two papers. Every
literature-backed statement must cite a supplied entity ID; label any new connection as a proposed
inference. Include boundary conditions, predicted outcome, uncertainty, and a falsifying experiment.
Prefer evidence units that contain an intact processing/composition -> structure -> mechanism ->
property chain. Never transfer an outcome across compositions, temperatures, environments, or
loading regimes without labeling that transfer as a proposed inference. State the controllable
intervention, expected structural change, mechanism, property direction, and applicable conditions.
Never treat METADATA_ONLY or REQUIRES_RESOLUTION citations as evidence from the cited paper, and
treat low-confidence raw table extraction as provisional.
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
    decision_use: str = ""
    required_facets: list[str] = field(default_factory=list)
    minimum_distinct_materials: int = 1
    depth: int = 0
    status: str = "pending"
    finding: str = ""
    decision: str = ""
    cited_ids: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


@dataclass
class EvidenceItem:
    node_id: str
    paper_id: str
    role: str
    content: str
    evidence_spans: list[str]
    score: float
    retrieval_reason: str
    source_contexts: list[dict[str, Any]] = field(default_factory=list)
    relation_context: dict[str, Any] = field(default_factory=dict)
    structured_context: dict[str, Any] = field(default_factory=dict)


def _default_tasks(goal: str) -> list[Task]:
    return [
        Task(
            "T1",
            f"What quantitative baseline property values are reported for materials relevant to '{goal}', and under exactly which temperature, environment, and loading conditions?",
            "baseline",
            [],
            ["evidence_result", "prior_approach"],
            "Establish the target metric, baseline range, and comparable operating regime.",
            ["material", "outcome", "conditions", "comparison", "provenance"],
            2,
        ),
        Task(
            "T2",
            f"Which intact processing or composition -> structure -> mechanism -> property chains explain the behavior targeted by '{goal}'?",
            "causal_chain",
            ["T1"],
            ["mechanism_principle", "causal_claim", "evidence_result"],
            "Identify causal levers without combining disconnected claims.",
            ["material", "intervention", "structure", "mechanism", "outcome", "conditions"],
            2,
        ),
        Task(
            "T3",
            f"Which controllable composition or processing changes improve the target property in '{goal}' relative to a stated baseline, by how much, and through which structural mechanism?",
            "intervention",
            ["T1", "T2"],
            ["causal_claim", "evidence_result", "hypothesis_statement"],
            "Select an actionable intervention and estimate its expected effect.",
            ["material", "intervention", "structure", "mechanism", "outcome", "comparison"],
            2,
        ),
        Task(
            "T4",
            f"At which temperatures, environments, times, or loading regimes do the candidate mechanisms for '{goal}' weaken, reverse, or fail?",
            "boundary",
            ["T2"],
            ["constraint", "contradiction", "prior_limitation"],
            "Define boundary conditions and reject unsafe extrapolation.",
            ["material", "mechanism", "outcome", "conditions", "limitations"],
            1,
        ),
        Task(
            "T5",
            f"Which competing mechanisms remain plausible for '{goal}', and which reported measurement or comparison can distinguish between them?",
            "discrimination",
            ["T3", "T4"],
            ["contradiction", "evidence_result", "mechanism_principle"],
            "Choose a falsifiable discriminator for the final hypothesis.",
            ["material", "mechanism", "outcome", "comparison", "provenance"],
            2,
        ),
    ]


def decompose_goal(goal: str) -> list[Task]:
    return _default_tasks(goal)


def retrieve_evidence(
    task: Task,
    graph: Graph,
    relation_index: dict[str, list[EvidenceRelation]] | None = None,
    entity_index: dict[str, EvidenceEntity] | None = None,
    context_index: dict[str, list[dict[str, Any]]] | None = None,
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

    evidence = [
        EvidenceItem(
            node_id=node.node_id,
            paper_id=node.paper_id,
            role=node.role,
            content=node.content,
            evidence_spans=node.evidence_spans,
            score=round(score, 4),
            retrieval_reason=reason,
        )
        for score, node, reason in selected + expanded
    ]

    if entity_index:
        typed_scored = []
        for entity in entity_index.values():
            if entity.entity_type in {"atomic_claim", "paper"}:
                continue
            terms = _keywords(f"{entity.name} {entity.description} {json.dumps(entity.attributes)}")
            overlap = len(query_terms & terms)
            if overlap:
                typed_scored.append((overlap, entity))
        typed_scored.sort(key=lambda value: (-value[0], value[1].entity_id))
        typed_paper_counts: dict[str, int] = {}
        for score, entity in typed_scored:
            if entity.entity_id in seen or typed_paper_counts.get(entity.source_paper_id, 0) >= MAX_PER_PAPER:
                continue
            seen.add(entity.entity_id)
            typed_paper_counts[entity.source_paper_id] = typed_paper_counts.get(entity.source_paper_id, 0) + 1
            evidence.append(EvidenceItem(
                node_id=entity.entity_id,
                paper_id=entity.source_paper_id,
                role=entity.entity_type,
                content=entity.description or entity.name,
                evidence_spans=[entity.evidence_span] if entity.evidence_span else [],
                score=float(score),
                retrieval_reason="typed_entity_seed",
            ))
            if sum(item.retrieval_reason == "typed_entity_seed" for item in evidence) >= MAX_DIRECT_HITS:
                break

    if relation_index:
        for seed in list(evidence):
            for relation in relation_index.get(seed.node_id, []):
                linked_ids = [relation.source_entity_id, *relation.target_entity_ids]
                for linked_id in linked_ids:
                    if linked_id in seen:
                        continue
                    seen.add(linked_id)
                    reason = f"typed_relation:{relation.relation_type}:{relation.relation_id}"
                    relation_context = {
                        "relation_id": relation.relation_id,
                        "relation_type": relation.relation_type,
                        "metric": relation.metric,
                        "subject_value": relation.subject_value,
                        "reference_value": relation.reference_value,
                        "unit": relation.unit,
                        "conditions": relation.conditions,
                        "evidence_span": relation.evidence_span,
                        "source_element": relation.source_element,
                        "confidence": relation.confidence,
                    }
                    if linked_id in graph.nodes:
                        node = graph.nodes[linked_id]
                        evidence.append(EvidenceItem(
                            node_id=node.node_id,
                            paper_id=node.paper_id,
                            role=node.role,
                            content=node.content,
                            evidence_spans=node.evidence_spans,
                            score=round(seed.score * relation.confidence, 4),
                            retrieval_reason=reason,
                            relation_context=relation_context,
                        ))
                    elif entity_index and linked_id in entity_index:
                        entity = entity_index[linked_id]
                        evidence.append(EvidenceItem(
                            node_id=entity.entity_id,
                            paper_id=entity.source_paper_id,
                            role=entity.entity_type,
                            content=entity.description or entity.name,
                            evidence_spans=[entity.evidence_span] if entity.evidence_span else [],
                            score=round(seed.score * relation.confidence, 4),
                            retrieval_reason=reason,
                            relation_context=relation_context,
                        ))
    if context_index:
        context_query_terms = _context_keywords(task.question)
        contextual_seeds: list[tuple[int, str, dict[str, Any]]] = []
        for context_id, contexts in context_index.items():
            if not context_id.startswith(("comparison:", "table:")):
                continue
            for context in contexts:
                overlap = len(context_query_terms & _context_keywords(
                    f"{context.get('text', '')} {context.get('evidence_span', '')}"
                ))
                if overlap:
                    contextual_seeds.append((overlap, context_id, context))
        contextual_seeds.sort(key=lambda value: (-value[0], value[1]))
        for score, context_id, context in contextual_seeds[:MAX_DIRECT_HITS]:
            if context_id in seen:
                continue
            seen.add(context_id)
            evidence.append(EvidenceItem(
                node_id=context_id,
                paper_id=context.get("paper_id", ""),
                role=f"{context.get('context_type', 'source')}_context",
                content=context.get("evidence_span") or context.get("text", ""),
                evidence_spans=[context.get("text", "")],
                score=float(score),
                retrieval_reason=f"{context.get('context_type', 'source')}_seed",
                source_contexts=[context],
            ))
        for item in evidence:
            if not item.source_contexts:
                item.source_contexts.extend(context_index.get(item.node_id, []))
    return evidence


def retrieve_materials_evidence(
    task: Task,
    units: list[MaterialsEvidenceUnit],
) -> list[EvidenceItem]:
    query_terms = _keywords(task.question)
    scored: list[tuple[float, MaterialsEvidenceUnit]] = []
    for unit in units:
        overlap = len(query_terms & _keywords(unit.summary()))
        matched_facets = len(set(task.required_facets) & unit.facets())
        if not overlap and not matched_facets:
            continue
        completeness = matched_facets / max(len(task.required_facets), 1)
        score = overlap + (3.0 * completeness) + unit.confidence
        scored.append((score, unit))
    scored.sort(key=lambda value: (-value[0], value[1].unit_id))

    selected: list[EvidenceItem] = []
    paper_counts: dict[str, int] = {}
    for score, unit in scored:
        if paper_counts.get(unit.paper_id, 0) >= MAX_PER_PAPER:
            continue
        selected.append(EvidenceItem(
            node_id=unit.unit_id,
            paper_id=unit.paper_id,
            role="materials_evidence_unit",
            content=unit.summary(),
            evidence_spans=unit.evidence_spans,
            score=round(score, 4),
            retrieval_reason="linked_materials_evidence",
            structured_context=unit.to_dict(),
        ))
        paper_counts[unit.paper_id] = paper_counts.get(unit.paper_id, 0) + 1
        if len(selected) >= MAX_DIRECT_HITS:
            break
    return selected


def retrieve_cited_role_evidence(task: Task, evidence: list[EvidenceItem]) -> list[EvidenceItem]:
    candidates: dict[str, tuple[float, dict[str, Any], dict[str, Any], EvidenceItem]] = {}
    for source_item in evidence:
        for context in source_item.source_contexts:
            for citation in context.get("citations", []):
                cited_paper_id = str(citation.get("resolved_paper_id", ""))
                for claim in citation.get("cited_role_context", []):
                    claim_id = str(claim.get("claim_id", ""))
                    if not claim_id or not cited_paper_id:
                        continue
                    role = str(claim.get("role", ""))
                    relevance = float(claim.get("relevance_score", 0))
                    role_bonus = 1.5 if role in task.required_roles else 0.0
                    score = source_item.score + relevance + role_bonus
                    current = candidates.get(claim_id)
                    if current is None or score > current[0]:
                        candidates[claim_id] = (score, claim, citation, source_item)

    ranked = sorted(candidates.values(), key=lambda value: (-value[0], str(value[1]["claim_id"])))
    return [EvidenceItem(
        node_id=str(claim["claim_id"]),
        paper_id=str(citation["resolved_paper_id"]),
        role=str(claim.get("role", "")),
        content=str(claim.get("content", "")),
        evidence_spans=[str(value) for value in claim.get("evidence_spans", []) if value],
        score=round(score, 4),
        retrieval_reason=f"cited_role:{source_item.node_id}:{citation.get('reference_id', '')}",
        relation_context={
            "relation_type": "cites",
            "source_entity_id": source_item.node_id,
            "resolved_paper_id": citation["resolved_paper_id"],
            "reference_id": citation.get("reference_id", ""),
            "reference_number": citation.get("reference_number", ""),
            "resolution_method": citation.get("resolution_method", ""),
            "confidence": 1.0,
        },
    ) for score, claim, citation, source_item in ranked[:MAX_CITATION_HITS]]


def _evidence_text(item: EvidenceItem) -> str:
    blocks = [f"id={item.node_id} paper={item.paper_id} role={item.role}: {item.content}"]
    if item.structured_context:
        blocks.append(
            "LINKED MATERIALS EVIDENCE (fields belong to one material state and regime):\n"
            f"{json.dumps(item.structured_context, ensure_ascii=False)}"
        )
    if item.relation_context:
        relation = item.relation_context
        if relation.get("relation_type") == "cites":
            blocks.append(
                f"CITATION PROVENANCE: source={relation.get('source_entity_id', '')}; "
                f"reference={relation.get('reference_number', '')}; "
                f"resolved_paper={relation.get('resolved_paper_id', '')}; "
                f"resolution={relation.get('resolution_method', '')}"
            )
        else:
            blocks.append(
                f"RELATION {relation.get('relation_type', '')}: metric={relation.get('metric') or 'unspecified'}; "
                f"subject={relation.get('subject_value')}; reference={relation.get('reference_value')}; "
                f"unit={relation.get('unit') or 'unspecified'}; conditions={relation.get('conditions') or {}}; "
                f"confidence={relation.get('confidence')}"
            )
    for context in item.source_contexts[:2]:
        blocks.append(
            f"SOURCE passage={context['passage_id']} section={context['section']} "
            f"match={context['match_score']}:\n{context['text']}"
        )
        if context["tables"]:
            blocks.append(
                "TABLE CONTEXT (raw extraction; obey each confidence field):\n"
                f"{json.dumps(context['tables'], ensure_ascii=False)}"
            )
        if context["citations"]:
            citations = []
            for citation in context["citations"]:
                status = citation.get("resolution_status", "unresolved").upper()
                cited_roles = citation.get("cited_role_context", [])
                if cited_roles:
                    role_evidence = "\n".join(
                        f"  - id={claim['claim_id']} role={claim['role']}: {claim['content']} "
                        f"(evidence: {' | '.join(value for value in claim.get('evidence_spans', []) if value)})"
                        for claim in cited_roles
                    )
                    citations.append(
                        f"{citation.get('mention_text') or '[' + citation.get('reference_number', '') + ']'} "
                        f"[LOCAL_EXTRACTION paper={citation.get('resolved_paper_id', '')}]:\n{role_evidence}"
                    )
                else:
                    citations.append(
                        f"{citation.get('mention_text', '')} [{status}; ROUTING_METADATA_ONLY]: "
                        f"{citation.get('reference_text', '')}"
                    )
            blocks.append("CITED REFERENCES:\n" + "\n".join(citations))
        if context.get("cited_content_status") == "requires_resolution":
            blocks.append("CITED CONTENT: REQUIRES_RESOLUTION; no cited-paper passage is available.")
    return "\n".join(blocks)


def assess_sufficiency(task: Task, evidence: list[EvidenceItem]) -> dict[str, Any]:
    evidence_block = "\n\n".join(f"- {_evidence_text(item)}" for item in evidence) or "(no evidence retrieved)"
    user = (
        f"TASK:\n{task.question}\n\nDECISION USE:\n{task.decision_use or '(not specified)'}\n\n"
        f"REQUIRED FACETS:\n{', '.join(task.required_facets) or '(legacy claim evidence)'}\n\n"
        f"MINIMUM DISTINCT MATERIALS OR BASELINES:\n{task.minimum_distinct_materials}\n\n"
        f"EVIDENCE:\n{evidence_block}"
    )
    result = resilient_chat_json(_SUFFICIENCY_SYSTEM, user, max_tokens=1200)
    if isinstance(result, dict) and result.get("decision") in SUFFICIENCY_DECISIONS:
        result.setdefault("assumptions", [])
        return result

    distinct_papers = {item.paper_id for item in evidence}
    decision = "reason_with_caveat" if len(evidence) >= 4 and len(distinct_papers) >= 2 else "unresolved"
    return {
        "decision": decision,
        "finding": f"Retrieved {len(evidence)} relevant entities from {len(distinct_papers)} papers; LLM synthesis was unavailable.",
        "cited_ids": [item.node_id for item in evidence[:6]],
        "reason": "Deterministic fallback based on evidence count and paper diversity.",
        "missing_questions": [],
        "assumptions": ["No domain-specific preference was supplied; conservative defaults were used."],
    }


def adjudicate_conflicts(goal: str, evidence: list[EvidenceItem]) -> dict[str, Any]:
    candidates = [item for item in evidence if item.role in {"contradiction", "rejected_alternative", "prior_limitation"}]
    if not candidates:
        return {"conflicts": []}
    block = "\n\n".join(f"- {_evidence_text(item)}" for item in candidates)
    result = resilient_chat_json(_ADJUDICATE_SYSTEM, f"GOAL:\n{goal}\n\nCLAIMS:\n{block}", max_tokens=1400)
    return result if isinstance(result, dict) and isinstance(result.get("conflicts"), list) else {"conflicts": []}


def select_synthesis_evidence(
    tasks: list[Task],
    evidence: list[EvidenceItem],
    limit: int = MAX_SYNTHESIS_EVIDENCE,
) -> list[EvidenceItem]:
    by_id = {item.node_id: item for item in evidence}
    selected: list[EvidenceItem] = []
    seen: set[str] = set()
    for task in tasks:
        for node_id in task.cited_ids:
            if node_id in by_id and node_id not in seen:
                selected.append(by_id[node_id])
                seen.add(node_id)
                if len(selected) >= limit:
                    return selected
    for item in sorted(evidence, key=lambda value: (-value.score, value.node_id)):
        if item.node_id not in seen:
            selected.append(item)
            seen.add(item.node_id)
            if len(selected) >= limit:
                break
    return selected


def synthesize(goal: str, tasks: list[Task], evidence: list[EvidenceItem], conflicts: dict[str, Any]) -> list[dict[str, Any]]:
    findings = "\n".join(
        f"- {task.task_id} [{task.decision}]: {task.finding} (citations: {', '.join(task.cited_ids)})"
        for task in tasks if task.finding
    )
    evidence_block = "\n\n".join(f"- {_evidence_text(item)}" for item in evidence)
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
    entities_path: Path | None = None,
    source_context_dir: Path | None = None,
    materials_evidence_path: Path | None = None,
) -> dict[str, Any]:
    graph = build_graph(outputs_dir)
    relations = load_relations(relations_path)
    relation_index = index_relations(relations)
    entities = load_entities(entities_path) if entities_path else []
    entity_index = {entity.entity_id: entity for entity in entities}
    context_index = load_context_index(source_context_dir)
    materials_units = load_materials_evidence(materials_evidence_path)
    tasks = decompose_goal(goal)
    trace: dict[str, Any] = {
        "run_id": str(uuid.uuid4()),
        "created_at": time.time(),
        "provider": provider_info(),
        "goal": goal,
        "subagents": [
            "planner_orchestrator", "evidence_researcher", "evidence_adjudicator",
            "hypothesis_synthesizer", "critic",
        ],
        "graph": {
            "nodes": len(graph.nodes),
            "papers": len({node.paper_id for node in graph.nodes.values()}),
            "typed_relations": len(relations),
            "typed_entities": len(entities),
            "contextualized_claims": len(context_index),
            "linked_materials_evidence_units": len(materials_units),
        },
        "events": [{
            "stage": "decompose",
            "agent": "planner_orchestrator",
            "tasks": [asdict(task) for task in tasks],
        }],
    }
    evidence_by_id: dict[str, EvidenceItem] = {}

    while any(task.status == "pending" for task in tasks):
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
            linked_evidence = retrieve_materials_evidence(task, materials_units)
            legacy_evidence = retrieve_evidence(task, graph, relation_index, entity_index, context_index)
            linked_ids = {item.node_id for item in linked_evidence}
            direct_evidence = linked_evidence + [
                item for item in legacy_evidence if item.node_id not in linked_ids
            ]
            citation_evidence = retrieve_cited_role_evidence(task, direct_evidence)
            direct_ids = {item.node_id for item in direct_evidence}
            evidence = direct_evidence + [item for item in citation_evidence if item.node_id not in direct_ids]
            for item in evidence:
                evidence_by_id[item.node_id] = item
            trace["events"].append({
                "stage": "citation_augmentation",
                "agent": "evidence_researcher",
                "task_id": task.task_id,
                "resolved_claims": [asdict(item) for item in citation_evidence],
            })
            assessment = assess_sufficiency(task, evidence)
            task.decision = str(assessment.get("decision", "unresolved"))
            task.finding = str(assessment.get("finding", ""))
            task.cited_ids = [str(value) for value in assessment.get("cited_ids", []) if str(value) in evidence_by_id]
            task.assumptions = [str(value) for value in assessment.get("assumptions", [])]
            task.status = "complete" if task.decision in {"sufficient", "reason_with_caveat"} else task.decision

            children: list[Task] = []
            if task.decision == "decompose_further" and task.depth < max_depth:
                for index, question in enumerate(assessment.get("missing_questions", []), start=1):
                    child_id = f"{task.task_id}.{index}"
                    children.append(Task(
                        task_id=child_id,
                        question=str(question),
                        intent="gap_closure",
                        depends_on=task.depends_on.copy(),
                        required_roles=task.required_roles.copy(),
                        decision_use=task.decision_use,
                        required_facets=task.required_facets.copy(),
                        minimum_distinct_materials=task.minimum_distinct_materials,
                        depth=task.depth + 1,
                    ))
                tasks.extend(children)
                task.status = "decomposed"

            trace["events"].append({
                "stage": "subtask",
                "agent": "evidence_researcher",
                "task_id": task.task_id,
                "question": task.question,
                "retrieved": [asdict(item) for item in evidence],
                "assessment": assessment,
                "children": [asdict(child) for child in children],
            })

    all_evidence = list(evidence_by_id.values())
    conflicts = adjudicate_conflicts(goal, all_evidence)
    trace["events"].append({"stage": "adjudication", "agent": "evidence_adjudicator", "conflicts": conflicts})
    synthesis_evidence = select_synthesis_evidence(tasks, all_evidence)
    trace["events"].append({
        "stage": "synthesis_evidence_selection",
        "agent": "hypothesis_synthesizer",
        "available_count": len(all_evidence),
        "selected_count": len(synthesis_evidence),
        "selected_ids": [item.node_id for item in synthesis_evidence],
    })
    candidates = synthesize(goal, tasks, synthesis_evidence, conflicts)
    valid_ids = set(evidence_by_id)
    candidate_records = []
    for candidate in candidates:
        cited_ids = [str(value) for value in candidate.get("cited_ids", []) if str(value) in valid_ids]
        candidate["cited_ids"] = cited_ids
        candidate["critics"] = critique(goal, candidate)
        candidate_records.append(candidate)
        trace["events"].append({
            "stage": "critique",
            "agent": "critic",
            "candidate_index": len(candidate_records) - 1,
            "result": candidate["critics"],
        })

    trace.update({
        "tasks": [asdict(task) for task in tasks],
        "conflicts": conflicts,
        "candidates": candidate_records,
        "status": "complete" if candidate_records else "complete_without_candidates",
    })
    trace["events"].append({
        "stage": "synthesis",
        "agent": "hypothesis_synthesizer",
        "candidate_count": len(candidate_records),
    })
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
    parser.add_argument("--entities", type=Path, help="optional JSONL file of typed evidence entities")
    parser.add_argument("--source-context", type=Path, help="optional directory of passage, citation, and table context bundles")
    parser.add_argument(
        "--materials-evidence",
        type=Path,
        help="optional linked materials evidence JSON file or directory",
    )
    args = parser.parse_args()
    result = run_workflow(
        args.goal,
        args.outputs_dir,
        args.trace_path,
        args.max_depth,
        args.relations,
        args.entities,
        args.source_context,
        args.materials_evidence,
    )
    print(f"[adaptive] status={result['status']} tasks={len(result['tasks'])} candidates={len(result['candidates'])}")
    print(f"[adaptive] trace={args.trace_path}")


if __name__ == "__main__":
    main()