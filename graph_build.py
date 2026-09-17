"""Build a cross-paper knowledge graph from the Stage-1 extraction outputs.

Every reconciled item, from every role, from every paper, becomes one typed
node - no paper-order, no role-order, no section-position is preserved. This
is deliberate: it's what lets the agent combine a `mechanism_principle` from
paper A with a `rejected_alternative` from paper C even though the two never
appeared anywhere near each other in the literature. Edges are lexical
(shared keyword) overlap, tagged same_paper vs cross_paper so retrieval can
explicitly prefer the latter (see hypothesis_agent.py).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "into", "over", "under",
    "than", "then", "when", "which", "while", "where", "these", "those", "there",
    "have", "has", "had", "was", "were", "are", "is", "be", "been", "being",
    "its", "their", "our", "not", "but", "can", "could", "would", "should",
    "does", "did", "due", "such", "also", "more", "most", "some", "each",
    "between", "across", "along", "within", "without", "both", "only", "even",
    "because", "however", "therefore", "thus", "hence", "shows", "show", "shown",
}

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z\-]{3,}")


def _keywords(text: str) -> set[str]:
    return {w for w in (m.group(0).lower() for m in _WORD_RE.finditer(text)) if w not in _STOPWORDS}


@dataclass
class Node:
    node_id: str
    paper_id: str
    role: str
    content: str
    evidence_spans: list[str]
    keywords: set[str] = field(default_factory=set)


@dataclass
class Graph:
    nodes: dict[str, Node]
    edges: dict[str, list[tuple[str, float, bool]]]  # node_id -> [(neighbor_id, weight, is_cross_paper)]


def build_graph(outputs_dir: Path, min_jaccard: float = 0.12, exclude: set[str] | None = None) -> Graph:
    exclude = exclude or set()
    nodes: dict[str, Node] = {}
    for record_path in sorted(outputs_dir.glob("*.json")):
        if record_path.stem in exclude:
            continue
        d = json.loads(record_path.read_text())
        paper_id = d["paper_id"]
        for role, items in d["reconciled_by_role"].items():
            for i, it in enumerate(items):
                content = it.get("content", "")
                if not content:
                    continue
                node_id = f"{paper_id}::{role}::{i}"
                nodes[node_id] = Node(
                    node_id=node_id, paper_id=paper_id, role=role, content=content,
                    evidence_spans=it.get("evidence_spans", []), keywords=_keywords(content),
                )

    edges: dict[str, list[tuple[str, float, bool]]] = {nid: [] for nid in nodes}
    ids = list(nodes.keys())
    for i, a_id in enumerate(ids):
        a = nodes[a_id]
        for b_id in ids[i + 1:]:
            b = nodes[b_id]
            if not a.keywords or not b.keywords:
                continue
            inter = a.keywords & b.keywords
            if not inter:
                continue
            jaccard = len(inter) / len(a.keywords | b.keywords)
            if jaccard >= min_jaccard:
                cross = a.paper_id != b.paper_id
                edges[a_id].append((b_id, jaccard, cross))
                edges[b_id].append((a_id, jaccard, cross))

    for nid in edges:
        edges[nid].sort(key=lambda e: -e[1])
    return Graph(nodes=nodes, edges=edges)


def graph_stats(g: Graph) -> str:
    n_cross_edges = sum(1 for nbrs in g.edges.values() for (_, _, cross) in nbrs if cross) // 2
    n_same_edges = sum(1 for nbrs in g.edges.values() for (_, _, cross) in nbrs if not cross) // 2
    papers = {n.paper_id for n in g.nodes.values()}
    return (f"nodes={len(g.nodes)} papers={len(papers)} "
            f"cross_paper_edges={n_cross_edges} same_paper_edges={n_same_edges}")
