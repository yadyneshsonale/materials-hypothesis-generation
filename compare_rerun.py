"""Experiment 21: every evaluation rerun on leak-free queries with a pre-cutoff generator, compared with the original.

Original (experiments 7, 9, 11, 14, 16, 17): experiment-3 queries (written from the held-out paper's results) and
generator Qwen3.5-35B-A3B (released February 2026, after the held-out papers).
Rerun (rerun_v3/): benchmark_v3 queries (introduction only, separate leakage checker; query_builder_v3.py) and
generator Llama-3.3-70B-Instruct (knowledge cutoff December 2023). Same hidden targets, corpus, evidence pools,
judges (GPT-5.6, DeepSeek-V4-Pro) and analysis.

For every arm the report gives the mean reconstruction score per level and overall (units = paper x level, samples
averaged), and paired comparisons within the rerun with the same statistics as before. It also re-runs the
experiment-19 check: does answer overlap in the query still predict the score?
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from failure_analysis import spearman
from hypothesis_evidence_v2 import atomic_json
from query_builder_v3 import raw_overlap
from temporal_eval_v3 import (EXPERIMENT_DIR, PRIMARY_DIMENSIONS, QUERY_LEVELS, cluster_bootstrap, exact_sign_test,
                              holm_adjust)
from temporal_hypothesis_benchmark import _read_json

OLD = EXPERIMENT_DIR
NEW = EXPERIMENT_DIR / "rerun_v3"
OUT = NEW / "comparison"
OLD_CASES = EXPERIMENT_DIR / "temporal_v2" / "benchmark_cases"
NEW_CASES = EXPERIMENT_DIR / "benchmark_v3" / "cases"
GATE_FAILED = {("PMC11355469", "expert_context"), ("PMC11606917", "expert_context")}

# experiment -> (subdirectory, run arm field, judge layout)
SOURCES = {
    "exp7_eval_v3": ("eval_v3", "setting", {"gpt": "judgments/absolute"}),
    "exp9_matkg": ("eval_v4_matkg", "setting", {"gpt": "judgments/absolute"}),
    "exp14_rubrics": ("rubric_eval", "arm", {"gpt": "judgments/gpt56", "deep": "judgments/deepseek"}),
    "exp16_improvements": ("improvements", "arm", {"gpt": "judgments/gpt56", "deep": "judgments/deepseek"}),
    "exp17_citegraph": ("citegraph", "arm", {"gpt": "judgments/gpt56", "deep": "judgments/deepseek"}),
}


def recon(scores: dict[str, int]) -> float:
    return statistics.fmean(scores[d] for d in PRIMARY_DIMENSIONS)


def load(root: Path) -> dict[str, dict[tuple[str, str, str], list[float]]]:
    """judge -> (experiment:arm, paper, level) -> list of reconstruction scores (one per sample)."""
    scores: dict[str, dict[tuple[str, str, str], list[float]]] = {"gpt": defaultdict(list), "deep": defaultdict(list)}
    for experiment, (sub, field, judges) in SOURCES.items():
        runs_dir = root / sub / "runs"
        for run_path in sorted(runs_dir.glob("PMC*.json")):
            run = _read_json(run_path)
            if run.get("status") != "ok":
                continue
            arm = run.get(field)
            if experiment == "exp9_matkg" and arm != "tool_agent_kg":
                continue
            for judge, folder in judges.items():
                path = root / sub / folder / run_path.name
                if path.exists():
                    scores[judge][(f"{experiment}:{arm}", run["paper_id"], run["query_level"])].append(
                        recon(_read_json(path)["scores"]))
    for arm in ("critique", "self_revise"):
        for path in sorted((root / "eval_critique" / "judgments" / arm).glob("PMC*.json")):
            j = _read_json(path)
            paper, level = path.stem.split("__")[:2]
            scores["gpt"][(f"exp11_critique:{arm}", paper, level)].append(recon(j["scores"]))
    for path in sorted((root / "eval_critique" / "baseline_resample" / "judgments" / "absolute").glob("PMC*.json")):
        paper, level = path.stem.split("__")[:2]
        scores["gpt"][("exp11_critique:tool_agent_resample", paper, level)].append(recon(_read_json(path)["scores"]))
    for path in sorted((root / "improvements" / "selections").glob("PMC*.json")):
        sel = _read_json(path)
        for judge, folder in (("gpt", "judgments/gpt56"), ("deep", "judgments/deepseek")):
            base = root / ("improvements" if sel["chosen_arm"] not in ("closed_book", "text_chunks", "card", "v2_units")
                           else "rubric_eval")
            jp = base / folder / f"{sel['paper_id']}__{sel['query_level']}__{sel['chosen_arm']}__s{sel['sample']}.json"
            if jp.exists():
                scores[judge][("exp16_improvements:ensemble_select", sel["paper_id"], sel["query_level"])].append(
                    recon(_read_json(jp)["scores"]))
    return {j: {k: v for k, v in d.items()} for j, d in scores.items()}


def units(scores: dict[tuple[str, str, str], list[float]], arm: str, levels: tuple[str, ...] = QUERY_LEVELS,
          exclude: set[tuple[str, str]] | None = None) -> dict[tuple[str, str], float]:
    return {(p, l): statistics.fmean(v) for (a, p, l), v in scores.items()
            if a == arm and l in levels and not (exclude and (p, l) in exclude)}


def mean(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 3) if values else None


def paired(a: dict, b: dict) -> dict[str, Any]:
    common = sorted(set(a) & set(b))
    per_paper: dict[str, list[float]] = defaultdict(list)
    for key in common:
        per_paper[key[0]].append(a[key] - b[key])
    if not per_paper:
        return {"units": 0}
    point, low, high = cluster_bootstrap(per_paper)
    p_value, pos, neg = exact_sign_test([statistics.fmean(v) for v in per_paper.values()])
    return {"units": len(common), "diff": round(point, 3), "ci95": [round(low, 3), round(high, 3)],
            "a_higher": pos, "b_higher": neg, "p": round(p_value, 4)}


def overlaps(cases_dir: Path) -> dict[tuple[str, str], float]:
    out = {}
    for path in sorted(cases_dir.glob("PMC*.json")):
        case = _read_json(path)
        for level in QUERY_LEVELS:
            out[(case["paper_id"], level)] = raw_overlap(case["queries"][level]["text"], case["hidden_target"])
    return out


def report() -> dict[str, Any]:
    old, new = load(OLD), load(NEW)
    ov_old, ov_new = overlaps(OLD_CASES), overlaps(NEW_CASES)
    arms = sorted({a for a, _, _ in new["gpt"]} | {a for a, _, _ in old["gpt"]})
    table = {}
    for arm in arms:
        row: dict[str, Any] = {}
        for name, data, ov in (("original", old, ov_old), ("rerun", new, ov_new)):
            u = units(data["gpt"], arm)
            ud = units(data["deep"], arm)
            row[name] = {"units": len(u), "gpt56": mean(list(u.values())), "deepseek": mean(list(ud.values())),
                         **{lvl: mean([v for k, v in u.items() if k[1] == lvl]) for lvl in QUERY_LEVELS},
                         "spearman_overlap_vs_score": round(spearman([ov[k] for k in sorted(u)],
                                                                     [u[k] for k in sorted(u)]), 3)
                         if len(u) > 3 else None,
                         "spearman_within_expert": round(spearman(
                             [ov[k] for k in sorted(u) if k[1] == "expert_context"],
                             [u[k] for k in sorted(u) if k[1] == "expert_context"]), 3)
                         if sum(1 for k in u if k[1] == "expert_context") > 3 else None}
        row["rerun_gate_passed_only"] = mean(list(units(new["gpt"], arm, exclude=GATE_FAILED).values()))
        table[arm] = row
    comparisons = {}
    for judge in ("gpt", "deep"):
        base = "exp14_rubrics:text_chunks"
        others = [a for a in arms if a.split(":")[0] in ("exp14_rubrics", "exp16_improvements", "exp17_citegraph")
                  and a != base and units(new[judge], a)]
        primary = [{"a": a, "b": base, **paired(units(new[judge], a), units(new[judge], base))} for a in others]
        for item, adj in zip(primary, holm_adjust([c.get("p", 1.0) for c in primary])):
            item["holm_p"] = round(adj, 4)
        v3_base = "exp7_eval_v3:closed_book"
        v3 = [{"a": a, "b": v3_base, **paired(units(new[judge], a), units(new[judge], v3_base))}
              for a in arms if a.startswith(("exp7", "exp9", "exp11")) and a != v3_base and units(new[judge], a)]
        closed = [{"a": a, "b": "exp14_rubrics:closed_book", **paired(units(new[judge], a),
                                                                       units(new[judge], "exp14_rubrics:closed_book"))}
                  for a in others if a != "exp14_rubrics:closed_book"]
        comparisons[judge] = {"vs_text_chunks": primary, "agents_vs_closed_book_v3": v3,
                              "vs_closed_book_exp14": closed}
    leakage = {lvl: {"original_mean_overlap": mean([v for k, v in ov_old.items() if k[1] == lvl]),
                     "rerun_mean_overlap": mean([v for k, v in ov_new.items() if k[1] == lvl])} for lvl in QUERY_LEVELS}
    analysis = {"table": table, "comparisons": comparisons, "query_overlap": leakage,
                "gate_failed_units": sorted(map(list, GATE_FAILED)), "factorial": factorial(),
                "agent_tool_use": agent_tool_use()}
    OUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / "analysis.json", analysis)
    (OUT / "tables.md").write_text(render(analysis))
    return analysis


FACTORIAL = {("qwen3.5 (post-cutoff)", "original leaky"): OLD / "eval_v3",
             ("llama-3.3 (pre-cutoff)", "original leaky"): NEW / "factorial" / "llama_oldq",
             ("qwen3.5 (post-cutoff)", "clean v3"): NEW / "factorial" / "qwen_newq",
             ("llama-3.3 (pre-cutoff)", "clean v3"): NEW / "eval_v3"}


def factorial() -> dict[str, Any]:
    """Experiment-7 settings under {generator} x {queries}: separates the query effect from the generator effect."""
    cells = {}
    unit_scores: dict[tuple[str, str], dict[tuple[str, str, str], float]] = {}
    for (generator, queries), root in FACTORIAL.items():
        scores = {}
        for path in (root / "judgments" / "absolute").glob("PMC*.json"):
            paper, level, setting = path.stem.split("__")[:3]
            scores[(paper, level, setting)] = recon(_read_json(path)["scores"])
        unit_scores[(generator, queries)] = scores
        cells[f"{generator}, {queries} queries"] = {
            "runs_judged": len(scores), "all": mean(list(scores.values())),
            **{setting: mean([v for k, v in scores.items() if k[2] == setting])
               for setting in ("closed_book", "text_oneshot", "v2_oneshot", "tool_agent")},
            **{level: mean([v for k, v in scores.items() if k[1] == level]) for level in QUERY_LEVELS}}

    def effect(a: tuple[str, str], b: tuple[str, str]) -> dict[str, Any]:
        per_paper: dict[str, list[float]] = defaultdict(list)
        # Sorted so the seeded bootstrap sees papers in the same order in every process (set order depends on
        # string hash randomisation).
        for key in sorted(set(unit_scores[a]) & set(unit_scores[b])):
            per_paper[key[0]].append(unit_scores[a][key] - unit_scores[b][key])
        point, low, high = cluster_bootstrap(per_paper)
        p_value, pos, neg = exact_sign_test([statistics.fmean(v) for v in per_paper.values()])
        return {"diff": round(point, 3), "ci95": [round(low, 3), round(high, 3)], "p": round(p_value, 4)}

    q, l = "qwen3.5 (post-cutoff)", "llama-3.3 (pre-cutoff)"
    effects = {"query_effect_qwen (clean - leaky)": effect((q, "clean v3"), (q, "original leaky")),
               "query_effect_llama (clean - leaky)": effect((l, "clean v3"), (l, "original leaky")),
               "generator_effect_leaky (llama - qwen)": effect((l, "original leaky"), (q, "original leaky")),
               "generator_effect_clean (llama - qwen)": effect((l, "clean v3"), (q, "clean v3"))}
    return {"cells": cells, "effects": effects}


def agent_tool_use() -> dict[str, Any]:
    out = {}
    for name, root in (("exp7 tool_agent original", OLD / "eval_v3"), ("exp7 tool_agent rerun", NEW / "eval_v3"),
                       ("exp9 tool_agent_kg original", OLD / "eval_v4_matkg"),
                       ("exp9 tool_agent_kg rerun", NEW / "eval_v4_matkg"),
                       ("exp7 tool_agent, Qwen on clean queries (factorial)", NEW / "factorial" / "qwen_newq")):
        setting = "tool_agent_kg" if "kg" in name else "tool_agent"
        runs = [r for r in (_read_json(p) for p in sorted((root / "runs").glob(f"PMC*__{setting}.json")))
                if r.get("status") == "ok"]
        out[name] = {"runs": len(runs), "tool_calls_mean": mean([r.get("tool_calls", 0) for r in runs]),
                     "zero_tool_call_runs": sum(1 for r in runs if not r.get("tool_calls")),
                     "records_cited_mean": mean([len(r.get("cited_evidence_ids", [])) for r in runs])}
    return out


def _f(x: Any) -> str:
    return "-" if x is None else (f"{x:.2f}" if isinstance(x, float) else str(x))


def render(a: dict[str, Any]) -> str:
    lines = ["# Rerun on leak-free queries with a pre-cutoff generator", "",
             "| query level | original overlap | rerun overlap |", "|---|---:|---:|"]
    for lvl, v in a["query_overlap"].items():
        lines.append(f"| {lvl} | {_f(v['original_mean_overlap'])} | {_f(v['rerun_mean_overlap'])} |")
    lines += ["", "## Factorial (experiment-7 settings): generator x queries", "",
              "| cell | runs | all | closed_book | text_oneshot | v2_oneshot | tool_agent | broad | problem | expert |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for cell, c in a["factorial"]["cells"].items():
        lines.append(f"| {cell} | {c['runs_judged']} | " + " | ".join(_f(c[k]) for k in (
            "all", "closed_book", "text_oneshot", "v2_oneshot", "tool_agent", *QUERY_LEVELS)) + " |")
    lines += ["", "| effect | diff | 95% CI | sign-test p |", "|---|---:|---|---:|"]
    for name, e in a["factorial"]["effects"].items():
        lines.append(f"| {name} | {_f(e['diff'])} | {e['ci95']} | {_f(e['p'])} |")
    lines += ["", "## Agent tool use", "", "| agent | runs | tool calls | runs with 0 calls | records cited |",
              "|---|---:|---:|---:|---:|"]
    for name, t in a["agent_tool_use"].items():
        lines.append(f"| {name} | {t['runs']} | {_f(t['tool_calls_mean'])} | {t['zero_tool_call_runs']} | "
                     f"{_f(t['records_cited_mean'])} |")
    lines += ["", "## Reconstruction score (GPT-5.6; DeepSeek where judged)", "",
              "| arm | orig GPT | orig DS | orig broad / problem / expert | orig ρ(overlap, score) | rerun GPT | rerun DS | "
              "rerun broad / problem / expert | rerun ρ | rerun ρ within expert | rerun, gate-passed units |",
              "|---|---:|---:|---|---:|---:|---:|---|---:|---:|---:|"]
    for arm, r in a["table"].items():
        o, n = r["original"], r["rerun"]
        lines.append(" | ".join([
            f"| {arm}", _f(o["gpt56"]), _f(o["deepseek"]),
            " / ".join(_f(o[l]) for l in QUERY_LEVELS), _f(o["spearman_overlap_vs_score"]),
            _f(n["gpt56"]), _f(n["deepseek"]), " / ".join(_f(n[l]) for l in QUERY_LEVELS),
            _f(n["spearman_overlap_vs_score"]), _f(n["spearman_within_expert"]), _f(r["rerun_gate_passed_only"])]) + " |")
    for judge, label in (("gpt", "GPT-5.6"), ("deep", "DeepSeek-V4-Pro")):
        for name, rows in a["comparisons"][judge].items():
            lines += ["", f"## Rerun paired comparisons, {name} ({label})", "",
                      "| a | b | units | diff | 95% CI | a higher | b higher | p | Holm p |", "|---|---|---:|---:|---|---:|---:|---:|---:|"]
            for c in rows:
                if c.get("units"):
                    lines.append(f"| {c['a']} | {c['b']} | {c['units']} | {_f(c['diff'])} | {c['ci95']} | "
                                 f"{c['a_higher']} | {c['b_higher']} | {_f(c['p'])} | {_f(c.get('holm_p'))} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    result = report()
    print((OUT / "tables.md").read_text())
