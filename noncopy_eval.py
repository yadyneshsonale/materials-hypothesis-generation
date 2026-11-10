"""Experiment 47 (loop.md 27.5): the non-copying metric replaces grounding (at the user's request, 2026-11-09).

Non-copying (1-5) asks whether a hypothesis merely copies the earlier literature (restates a passage's result,
proposes what a passage already did or proposed, takes a passage's mechanism word for word, or offers a textbook or
trivial idea) or goes beyond it (combines findings of several papers, transfers an idea with a reason, links the
evidence through an unstated mechanism, resolves a conflict or gap, or proposes something new). The judge
(DeepSeek-V4-Pro, one call) sees the question, the hypothesis and every passage the focused-retrieval writer was given
for that question (about 45 passages, 58,000 characters), labelled P1, P2, ...; a hypothesis written without evidence
is checked against the same passages. The judge is not told whether the hypothesis's author saw them.

SP2 = mean(plausibility, testability, usefulness, non-copying) - 1, on 0-4 (RQ scales: rq_judge, three DeepSeek calls).
Pairwise v2: the experiment-46 pairwise prompt with criterion (4) "well grounded" replaced by non-copying.

Stages (resumable; at most 6 workers per model):
  python noncopy_eval.py noncopy [--method M ...]                non-copying scores, DeepSeek
  python noncopy_eval.py pairwise --judge deepseek|gpt56         rx_r vs the closed-book writer, pairwise v2
  python noncopy_eval.py report                                  loop_quality/analysis_noncopy.{json,md}
"""

from __future__ import annotations

import quality_eval as Q  # noqa: I001 - first: it sets the case and loop roots before hypo_loop is imported

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

import diag_analysis as D
import focused_search as FS
import hypo_loop as H
import llm_client as lc
import loop_methods as LM
import refine_loop as RL
import rq_judge as RQ
import rubric_eval as rx
from hypothesis_evidence_v2 import atomic_json
from stage_metrics import CROSS_JUDGE
from temporal_hypothesis_benchmark import _read_json

A, V = Q.A, Q.V
OUT = Q.OUT
NONCOPY_DIR = OUT / "noncopy"
PAIR_DIR = OUT / "pairwise_v2"
DEV = Q.DEV
BEST, WRITER = "rx_r", Q.WRITER
METHODS = (BEST, WRITER)
SCALES = Q.SCALES
PARTS = ("intervention", "mechanism", "predicted_outcome", "falsification_test", "overall_idea")

NONCOPY_SYSTEM = """You are an experienced materials scientist judging whether a research hypothesis on high-temperature high-entropy alloys goes beyond the earlier literature or merely copies it. You see the research question, the hypothesis (as JSON; any evidence IDs in it refer to the passages) and passages from earlier papers relevant to the question, labelled P1, P2, and so on. The author of the hypothesis may or may not have seen these passages.

First trace where each part of the hypothesis comes from: its intervention, mechanism, predicted outcome, falsification test and overall idea. For each part, name the passages it is taken from, or say "general knowledge" if it is a textbook or very well-known idea, or "new" if neither.

A hypothesis copies when its core idea:
- restates a result that a passage reports, as if it were a prediction;
- proposes the same intervention on the same or a very similar material as a passage already studied;
- proposes what a passage already proposes as future work;
- takes its mechanism word for word from a passage;
- is a textbook or very well-known approach, or is trivial, obvious or generic.

A hypothesis goes beyond the evidence when it:
- combines findings from two or more different papers into one new proposal;
- transfers an idea to a new alloy or regime, with a reason it should work there;
- links the evidence through a mechanism that none of the passages states;
- proposes a test that resolves a conflict or gap between passages;
- proposes a non-trivial idea that no passage and no textbook contains.

Non-copying (1-5):
1 = Copied: the core idea restates one passage's result, study or proposed future work, or is a textbook or trivial idea
2 = Mostly copied: the core idea comes from one passage or from common knowledge, with only minor changes (a different amount, condition or wording), or its mechanism is taken word for word from a passage
3 = Partly new: a recognisable idea from the passages or common knowledge, with a substantive new element (a new material, regime or mechanism) but little justification or integration
4 = Synthesis: combines findings from two or more papers, transfers an idea to a new material or regime with a stated reason, or links the evidence through a mechanism none of the passages states
5 = Beyond the evidence: a non-trivial idea that no passage or textbook contains, or an integration of several sources into a proposal none of them suggests, for example one that resolves a conflict or gap between them

Rate only how far the hypothesis goes beyond the literature. Do not rate whether it is plausible, testable, useful or well written; other judges rate those. Length and the number of citations do not matter.

Return JSON: {"provenance": {"intervention": "passages, general knowledge or new", "mechanism": "...", "predicted_outcome": "...", "falsification_test": "...", "overall_idea": "..."}, "copied_elements": ["each element taken from a passage or from common knowledge, in a few words"], "non_copying_reason": "one or two sentences", "non_copying": integer 1-5}. Give the reason before the score."""

# The experiment-46 pairwise prompt with criterion (4) "well grounded" replaced by non-copying (loop.md 27.5).
_OLD_4 = ("(4) is it well grounded: claims consistent with established knowledge and with any cited evidence, and no "
          "invented precise values presented as fact; ")
_NEW_4 = ("(4) does it go beyond the earlier work: it combines or extends prior findings rather than restating a cited "
          "result, repeating what a cited paper already did or proposed, or offering a textbook or trivial idea; ")
if _OLD_4 not in D.QUALITY_PAIR_SYSTEM:
    raise RuntimeError("the pairwise prompt changed; update the criterion replacement")
PAIR_SYSTEM_V2 = D.QUALITY_PAIR_SYSTEM.replace(_OLD_4, _NEW_4)


# ---------------------------------------------------------------- the judge

def pack(paper: str, level: str) -> list[Any]:
    """The focused-retrieval writer's evidence for a question (refine_loop.start_pack with focused=True)."""
    return RL.fit_budget(FS.pack_records(paper, level), RL.BUDGET)


def view(run: dict[str, Any]) -> dict[str, Any]:
    """The question, the hypothesis with evidence IDs relabelled to the passages' labels, and the passages."""
    records = pack(run["paper_id"], run["query_level"])
    labels = {r.record_id: f"P{n + 1}" for n, r in enumerate(records)}
    if run["method"] == BEST and sorted(labels) != sorted(run["seen_ids"]):
        raise RuntimeError(f"{run['run_id']}: the rebuilt evidence differs from what the writer saw")
    generation = {k: v for k, v in run["generation"].items() if k != "citation_validation"}
    for field in ("supporting_evidence_ids", "conflicting_evidence_ids"):
        generation[field] = [labels[i] for i in generation.get(field, []) if i in labels]
    cap = rx.record_cap("text_chunks")
    passages = []
    for r in records:
        item = LM.v2_item(r, cap)
        passages.append({"id": labels[r.record_id], "paper_title": item["paper_title"], "section": item["section"],
                         "publication_date": item["publication_date"], "text": item["evidence"]})
    return {"query": run["query"], "generation": generation, "passages": passages}


def payload(data: dict[str, Any]) -> str:
    text = json.dumps({"research_question": data["query"], "hypothesis": data["generation"],
                       "earlier_passages": data["passages"]}, ensure_ascii=False)
    if "hidden_target" in text:
        raise H.TargetLeak("non-copying payload must not contain the answer key")
    return text


def validate(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    try:
        value = int(raw.get("non_copying"))
    except (TypeError, ValueError):
        return None
    if not 1 <= value <= 5 or float(raw.get("non_copying")) != value:
        return None
    prov = raw.get("provenance") if isinstance(raw.get("provenance"), dict) else {}
    copied = raw.get("copied_elements") if isinstance(raw.get("copied_elements"), list) else []
    return {"non_copying": value, "reason": str(raw.get("non_copying_reason", ""))[:800],
            "provenance": {p: str(prov.get(p, ""))[:300] for p in PARTS},
            "copied_elements": [str(c)[:200] for c in copied[:8]]}


def call(judge: str, user: str) -> Any:
    if judge == "deepseek":
        return lc.trapi_chat_json(CROSS_JUDGE["deployment"], NONCOPY_SYSTEM, user, max_tokens=4000,
                                  token_field=CROSS_JUDGE["token_field"], temperature=CROSS_JUDGE["temperature"],
                                  retries=8)
    if judge == "gpt56":
        return lc.judge_chat_json(NONCOPY_SYSTEM, user, max_tokens=8000)
    raise ValueError(f"unknown non-copying judge {judge!r}")


def judge(judge_name: str, data: dict[str, Any], attempts: int = 3) -> dict[str, Any]:
    user = payload(data)
    for attempt in range(attempts):
        result = validate(call(judge_name, user))
        if result is not None:
            return {"judge": judge_name, **result, "passages": len(data["passages"]), "attempts": attempt + 1}
    raise lc.LLMError(f"non-copying judge {judge_name} gave no valid score in {attempts} attempts")


def path_of(method: str, judge_name: str, run_id: str, root: Path | None = None) -> Path:
    return (root or NONCOPY_DIR) / method / judge_name / f"{run_id}.json"


def noncopy_stage(methods: list[str], judge_name: str, workers: int) -> dict[str, int]:
    jobs = Q._order([(path_of(m, judge_name, r["run_id"]), r) for m in methods for r in RQ.runs_of(m)
                     if not path_of(m, judge_name, r["run_id"]).exists()])

    def job(j: tuple[Path, dict[str, Any]]) -> None:
        path, run = j
        if not path.exists():
            H.write_once(path, {"run_id": run["run_id"], **judge(judge_name, view(run))})

    return Q._run(jobs, job, workers, f"noncopy-{judge_name}")


def load(method: str, judge_name: str = DEV) -> dict[tuple[str, str, int], dict[str, Any]]:
    folder = NONCOPY_DIR / method / judge_name
    return {Q.key_of_item(p.stem): _read_json(p) for p in sorted(folder.glob("*.json"))} if folder.exists() else {}


# ---------------------------------------------------------------- scores and report

def sp2_values(method: str) -> dict[tuple[str, str, int], float]:
    rq, nc = Q.rq_values(method), load(method)
    return {k: (sum(x["scores"][s] for s in SCALES) + nc[k]["non_copying"]) / 4 - 1 for k, x in rq.items() if k in nc}


def summary(method: str) -> dict[str, Any]:
    nc = load(method)
    if not nc:
        return {"judged": 0}
    values = [x["non_copying"] for x in nc.values()]
    sources = Counter()
    for x in nc.values():
        idea = x["provenance"]["overall_idea"].lower()
        sources["new" if idea.startswith("new") else "general knowledge" if "general knowledge" in idea
                else "passages"] += 1
    return {"judged": len(nc), "runs": len(RQ.runs_of(method)),
            "non_copying": Q.mean_of(Q.per_paper({k: float(x["non_copying"]) for k, x in nc.items()})),
            "distribution": dict(sorted(Counter(values).items())),
            "overall_idea_source": dict(sources),
            "sp2": Q.mean_of(Q.per_paper(sp2_values(method))),
            "sp_with_grounding": Q.mean_of(Q.per_paper(Q.sp_values(method))),
            "rq": Q.mean_of(Q.per_paper({k: x["rq"] for k, x in Q.rq_values(method).items()}))}


def examples(method: str, n: int = 2) -> list[dict[str, Any]]:
    nc = load(method)
    out = []
    for score in (min(x["non_copying"] for x in nc.values()), max(x["non_copying"] for x in nc.values())) if nc else ():
        for key, x in sorted(nc.items()):
            if x["non_copying"] == score and len([o for o in out if o["score"] == score]) < n:
                run = _read_json(RQ.root_of(method) / method / "runs" / f"{x['run_id']}.json")
                out.append({"run_id": x["run_id"], "score": score, "intervention": run["generation"]["intervention"],
                            "reason": x["reason"], "overall_idea": x["provenance"]["overall_idea"]})
    return out


def report() -> dict[str, Any]:
    nc_best, nc_writer = load(BEST), load(WRITER)
    pairs = {j: Q.pair_result(BEST, WRITER, j, PAIR_DIR) for j in ("deepseek", "gpt56")}
    old_pairs = {j: Q.pair_result(BEST, WRITER, j) for j in ("deepseek", "gpt56", "o1")}
    return {
        "methods": {m: summary(m) for m in METHODS},
        "non_copying_vs_writer": A.paired(Q.per_paper({k: float(x["non_copying"]) for k, x in nc_best.items()}),
                                          Q.per_paper({k: float(x["non_copying"]) for k, x in nc_writer.items()}))
        if nc_best and nc_writer else {"papers": 0},
        "sp2_vs_writer": A.paired(Q.per_paper(sp2_values(BEST)), Q.per_paper(sp2_values(WRITER)))
        if nc_best and nc_writer else {"papers": 0},
        "pairwise_v2": pairs, "pairwise_v1_experiment46": old_pairs,
        "examples": {m: examples(m) for m in METHODS},
        "validated": False,
    }


def _c(x: dict[str, Any]) -> str:
    if not x or not x.get("papers"):
        return "–"
    return f"{x['diff']:+.2f} [{x['ci95'][0]:+.2f}, {x['ci95'][1]:+.2f}], {x['up']} vs {x['down']} papers, p {x['p']}"


def render(r: dict[str, Any]) -> str:
    L = ["# Experiment 47: non-copying replaces grounding", "",
         "Pre-registered in loop.md 27.5. Non-copying (1-5, DeepSeek, one call) judges whether a hypothesis goes beyond "
         "the earlier literature (every passage the focused-retrieval writer was given for the question) or copies it. "
         "SP2 = mean(plausibility, testability, usefulness, non-copying) - 1, on 0-4. **The metric is not validated** "
         "(the user chose no validation controls).", "",
         "| | Non-copying (1–5) | Distribution 1/2/3/4/5 | Overall idea from: passages / general knowledge / new | SP2 | "
         "SP with grounding (exp. 46) | RQ |", "|---|---:|---|---|---:|---:|---:|"]
    for m, x in r["methods"].items():
        if not x.get("judged"):
            L.append(f"| `{m}` | – | – | – | – | – | – |")
            continue
        d = x["distribution"]
        s = x["overall_idea_source"]
        L.append(f"| `{m}` ({x['judged']} of {x['runs']}) | {x['non_copying']:.2f} | "
                 f"{'/'.join(str(d.get(k, 0)) for k in range(1, 6))} | {s.get('passages', 0)} / "
                 f"{s.get('general knowledge', 0)} / {s.get('new', 0)} | {x['sp2']:.2f} | {x['sp_with_grounding']:.2f} | "
                 f"{x['rq']:.2f} |")
    L += ["", f"- Non-copying, `{BEST}` minus the writer (paired by paper): {_c(r['non_copying_vs_writer'])}",
          f"- SP2, `{BEST}` minus the writer: {_c(r['sp2_vs_writer'])}", "",
          f"## Pairwise v2: `{BEST}` vs the closed-book writer (both orders; a win needs both)", ""]
    for j, x in r["pairwise_v2"].items():
        L.append(f"- {j}: {_c(x)}; pairs {x.get('pairs', 0)}, {BEST} wins {x.get('new_wins')}, writer wins "
                 f"{x.get('base_wins')}")
    L += ["", "For comparison, the experiment-46 prompt (criterion 4 = well grounded):"]
    for j, x in r["pairwise_v1_experiment46"].items():
        L.append(f"- {j}: {_c(x)}")
    L += ["", "## Examples (lowest and highest scores)", ""]
    for m, items in r["examples"].items():
        for e in items:
            L.append(f"- `{m}` {e['run_id']} — **{e['score']}**: {e['intervention'][:200]} *Judge:* {e['reason'][:300]}")
    return "\n".join(L) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("noncopy", "pairwise", "report"))
    parser.add_argument("--method", action="append")
    parser.add_argument("--judge", default=DEV, choices=("deepseek", "gpt56"))
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.stage == "noncopy":
        print(noncopy_stage(args.method or list(METHODS), args.judge, args.workers))
    elif args.stage == "pairwise":
        print(Q.pairwise_stage([BEST], args.judge, args.workers, WRITER, PAIR_SYSTEM_V2, PAIR_DIR))
    else:
        result = report()
        atomic_json(OUT / "analysis_noncopy.json", result)
        (OUT / "analysis_noncopy.md").write_text(render(result))
        print(render(result))


if __name__ == "__main__":
    main()
