"""MatKG-augmented tool agent (tool_agent_kg) compared with the v3 baselines.

The KG setting is the v3 tool agent plus a kg_lookup tool. kg_lookup returns co-occurrence facts from
MatKG (CC BY 4.0) that were built only from papers published before the cutoff year, and never from the
held-out paper's DOI or its work family. A fact is a readable record, so the same read-before-cite rule
applies to KG facts as to paper text.

Baseline runs and their absolute judgments come from the v3 evaluation (same generator, judge and blinding
code), so this module generates and judges only the new setting, then compares it with each baseline on the
same paper-by-query units.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from hypothesis_evidence_v2 import atomic_json
from temporal_eval_v3 import (
    CASES_DIR,
    RUN_ROOT,
    ALL_DIMENSIONS,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    EXPERIMENT_DIR,
    PRIMARY_DIMENSIONS,
    QUERY_LEVELS,
    SCHEMA_VERSION,
    cluster_bootstrap,
    exact_sign_test,
    generate_all,
    holm_adjust,
    judge_all,
    mean,
    _load_dir,
)
from temporal_hypothesis_benchmark import _read_json

KG_SETTING = "tool_agent_kg"
BASELINES = ("closed_book", "text_oneshot", "v2_oneshot", "tool_agent")
KG_PAIRS = tuple((KG_SETTING, baseline) for baseline in BASELINES)
METADATA = EXPERIMENT_DIR / "temporal_v2" / "temporal_metadata.json"
V2_DIR = EXPERIMENT_DIR / "temporal_v2" / "materials_evidence_v2"
PAPER_MAPS = EXPERIMENT_DIR / "section_aware" / "paper_maps"
SOURCE_V3 = RUN_ROOT / "eval_v3"
OUTPUT_V4 = RUN_ROOT / "eval_v4_matkg"
DEFAULT_KG_DB = Path.home() / "matkg_index" / "entdoi.sqlite"


def prepare(source: Path, output: Path) -> dict[str, int]:
    """Copy baseline runs and their absolute judgments from the v3 evaluation."""
    for sub in ("runs", "judgments/absolute", "judgments/pairwise"):
        (output / sub).mkdir(parents=True, exist_ok=True)
    copied_runs = copied_judgments = 0
    for run_path in sorted((source / "runs").glob("PMC*.json")):
        if _read_json(run_path)["setting"] not in BASELINES:
            continue
        shutil.copy2(run_path, output / "runs" / run_path.name)
        copied_runs += 1
        judgment = source / "judgments" / "absolute" / run_path.name
        if judgment.exists():
            shutil.copy2(judgment, output / "judgments" / "absolute" / judgment.name)
            copied_judgments += 1
    return {"runs_copied": copied_runs, "absolute_judgments_copied": copied_judgments}


def generate(output: Path, kg_db: Path, workers: int, resume: bool) -> dict[str, int]:
    return generate_all(
        cases_dir=CASES_DIR, metadata_path=METADATA, v2_dir=V2_DIR, paper_maps_dir=PAPER_MAPS,
        output_dir=output, settings=(KG_SETTING,), levels=QUERY_LEVELS, case_ids=None,
        workers=workers, resume=resume, kg_db=kg_db,
    )


def judge(output: Path, workers: int, resume: bool) -> dict[str, int]:
    return judge_all(cases_dir=CASES_DIR, output_dir=output, workers=workers, resume=resume, pairs=KG_PAIRS)


def _kg_ids(ids: list[str]) -> list[str]:
    return [item for item in ids if item.startswith("KG::")]


def analyze(*, cases_dir: Path, output_dir: Path) -> dict[str, Any]:
    loaded = [_read_json(path) for path in sorted(cases_dir.glob("PMC*.json"))]
    cases = {case["paper_id"]: case for case in loaded if "queries" in case}
    settings = (KG_SETTING,) + BASELINES
    expected_runs = len(cases) * len(QUERY_LEVELS) * len(settings)
    runs = _load_dir(output_dir / "runs")
    absolute = _load_dir(output_dir / "judgments" / "absolute")
    pairwise = _load_dir(output_dir / "judgments" / "pairwise")
    errors = _load_dir(output_dir / "judgments" / "errors")

    rows = []
    for run_id, run in runs.items():
        judgment = absolute.get(run_id)
        row = {"run_id": run_id, "paper_id": run["paper_id"], "query_level": run["query_level"],
               "setting": run["setting"], "status": run["status"], "judged": judgment is not None,
               "tool_calls": run["tool_calls"], "accessed": len(run["accessed_record_ids"]),
               "kg_surfaced": len(_kg_ids(run["accessed_record_ids"])),
               "kg_cited": len(_kg_ids(run["cited_evidence_ids"]))}
        if judgment:
            scores = judgment["scores"]
            row["reconstruction_mean"] = mean([scores[d] for d in PRIMARY_DIMENSIONS])
            row["overall_mean"] = mean([scores[d] for d in ALL_DIMENSIONS])
            row["classification"] = judgment["classification"]
        rows.append(row)

    by_setting: dict[str, Any] = {}
    for setting in settings:
        selected = [row for row in rows if row["setting"] == setting]
        judged = [row for row in selected if row["judged"]]
        classes: dict[str, int] = defaultdict(int)
        for row in judged:
            classes[row["classification"]] += 1
        by_setting[setting] = {
            "runs_expected": len(cases) * len(QUERY_LEVELS),
            "runs_present": len(selected),
            "runs_failed": sum(1 for row in selected if row["status"] != "ok"),
            "runs_judged": len(judged),
            "reconstruction_mean": round(mean([r["reconstruction_mean"] for r in judged]), 4),
            "overall_mean": round(mean([r["overall_mean"] for r in judged]), 4),
            "classifications": dict(classes),
            "mean_tool_calls": round(mean([r["tool_calls"] for r in selected]), 2),
            "mean_accessed_records": round(mean([r["accessed"] for r in selected]), 2),
            "mean_kg_facts_surfaced": round(mean([r["kg_surfaced"] for r in selected]), 2),
            "runs_citing_kg_facts": sum(1 for r in selected if r["kg_cited"] > 0),
            "kg_facts_cited_total": sum(r["kg_cited"] for r in selected),
        }

    units: dict[str, dict[tuple[str, str], float]] = defaultdict(dict)
    for row in rows:
        if row["judged"]:
            units[row["setting"]][(row["paper_id"], row["query_level"])] = row["reconstruction_mean"]
    comparisons = []
    for baseline in BASELINES:
        common = sorted(set(units[KG_SETTING]) & set(units[baseline]))
        per_paper: dict[str, list[float]] = defaultdict(list)
        for key in common:
            per_paper[key[0]].append(units[KG_SETTING][key] - units[baseline][key])
        if not per_paper:
            continue
        paper_diffs = [mean(values) for values in per_paper.values()]
        point, low, high = cluster_bootstrap(per_paper)
        p_value, positive, negative = exact_sign_test(paper_diffs)
        comparisons.append({
            "a": KG_SETTING, "b": baseline, "units": len(common), "papers": len(per_paper),
            "mean_difference": round(point, 4), "ci95_cluster_bootstrap": [round(low, 4), round(high, 4)],
            "papers_a_higher": positive, "papers_b_higher": negative,
            "sign_test_p_two_sided": round(p_value, 4),
        })
    for item, adjusted in zip(comparisons, holm_adjust([c["sign_test_p_two_sided"] for c in comparisons])):
        item["holm_adjusted_p"] = round(adjusted, 4)

    pairwise_summary = []
    for baseline in BASELINES:
        judgments = [j for j in pairwise.values() if j["setting_a"] == KG_SETTING and j["setting_b"] == baseline]
        wins = sum(1 for j in judgments if j["outcome"] == KG_SETTING)
        losses = sum(1 for j in judgments if j["outcome"] == baseline)
        pairwise_summary.append({
            "a": KG_SETTING, "b": baseline, "judged_units": len(judgments), "a_wins": wins, "b_wins": losses,
            "ties": sum(1 for j in judgments if j["outcome"] == "tie"),
            "position_inconsistent": sum(1 for j in judgments if j["consistency"] != "consistent"),
            "a_win_rate_excluding_ties": round(wins / (wins + losses), 4) if wins + losses else None,
        })

    all_runs = list(runs.values())
    integrity = {
        "schema_version": SCHEMA_VERSION,
        "expected_runs": expected_runs,
        "runs_present": len(runs),
        "runs_failed": sum(1 for run in all_runs if run["status"] != "ok"),
        "runs_judged": len(absolute),
        "pairs_expected": len(cases) * len(QUERY_LEVELS) * len(BASELINES),
        "pairs_judged": len(pairwise),
        "judge_errors": len(errors),
        "temporal_violations": sum(run["audit"]["temporal_violations"] for run in all_runs),
        "test_paper_leaks": sum(run["audit"]["test_paper_leaks"] for run in all_runs),
        "family_leaks": sum(run["audit"]["family_leaks"] for run in all_runs),
        "unknown_record_ids": sum(run["audit"]["unknown_record_ids"] for run in all_runs),
        "invalid_citations": sum(run["audit"]["invalid_citations"] for run in all_runs),
        "query_leaks": sum(run["audit"]["query_leak"] for run in all_runs),
        "generators": sorted({run["generator"] for run in all_runs}),
        "judges": sorted({j["judge"] for j in [*absolute.values(), *pairwise.values()]}),
    }
    integrity["verified"] = bool(
        integrity["runs_present"] == expected_runs
        and integrity["runs_failed"] == 0
        and integrity["runs_judged"] == expected_runs
        and integrity["pairs_judged"] == integrity["pairs_expected"]
        and integrity["judge_errors"] == 0
        and all(integrity[key] == 0 for key in (
            "temporal_violations", "test_paper_leaks", "family_leaks", "unknown_record_ids",
            "invalid_citations", "query_leaks"))
        and len(integrity["generators"]) == 1 and len(integrity["judges"]) == 1
    )
    analysis = {"schema_version": SCHEMA_VERSION, "cases": len(cases), "query_levels": list(QUERY_LEVELS),
                "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED},
                "by_setting": by_setting, "comparisons": comparisons, "pairwise": pairwise_summary,
                "integrity": integrity}
    results = output_dir / "results"
    results.mkdir(parents=True, exist_ok=True)
    atomic_json(results / "analysis_kg.json", analysis)
    atomic_json(results / "integrity_kg.json", integrity)
    (results / "summary_kg.md").write_text(render_summary(analysis))
    return analysis


def render_summary(analysis: dict[str, Any]) -> str:
    integrity = analysis["integrity"]
    lines = [
        f"Integrity verified: {integrity['verified']}. Runs judged {integrity['runs_judged']}/{integrity['expected_runs']}; "
        f"pairs judged {integrity['pairs_judged']}/{integrity['pairs_expected']}; failed runs {integrity['runs_failed']}; "
        f"judge errors {integrity['judge_errors']}; generator {', '.join(integrity['generators'])}; "
        f"judge {', '.join(integrity['judges'])}.",
        "",
        "| Setting | Runs judged | Reconstruction (0-4) | Overall (0-4) | Failed | Tool calls | Records accessed | KG facts surfaced per run | Runs citing a KG fact | KG facts cited |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for setting, row in analysis["by_setting"].items():
        lines.append(f"| {setting} | {row['runs_judged']}/{row['runs_expected']} | {row['reconstruction_mean']:.2f} | "
                     f"{row['overall_mean']:.2f} | {row['runs_failed']} | {row['mean_tool_calls']:.1f} | "
                     f"{row['mean_accessed_records']:.1f} | {row['mean_kg_facts_surfaced']:.1f} | "
                     f"{row['runs_citing_kg_facts']} | {row['kg_facts_cited_total']} |")
    lines += ["", "| A | B | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p |",
              "|---|---|---:|---:|---|---:|---:|---:|"]
    for item in analysis["comparisons"]:
        low, high = item["ci95_cluster_bootstrap"]
        lines.append(f"| {item['a']} | {item['b']} | {item['units']} | {item['mean_difference']:+.2f} | "
                     f"[{low:+.2f}, {high:+.2f}] | {item['papers_a_higher']} / {item['papers_b_higher']} | "
                     f"{item['sign_test_p_two_sided']:.3f} | {item['holm_adjusted_p']:.3f} |")
    lines += ["", "| A | B | Judged units | A wins | B wins | Ties | Position-inconsistent | A win rate (no ties) |",
              "|---|---|---:|---:|---:|---:|---:|---:|"]
    for item in analysis["pairwise"]:
        rate = "n/a" if item["a_win_rate_excluding_ties"] is None else f"{item['a_win_rate_excluding_ties']:.2f}"
        lines.append(f"| {item['a']} | {item['b']} | {item['judged_units']} | {item['a_wins']} | {item['b_wins']} | "
                     f"{item['ties']} | {item['position_inconsistent']} | {rate} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--source", type=Path, default=SOURCE_V3)
    prep.add_argument("--output", type=Path, default=OUTPUT_V4)
    gen = sub.add_parser("generate")
    gen.add_argument("--output", type=Path, default=OUTPUT_V4)
    gen.add_argument("--kg-db", type=Path, default=DEFAULT_KG_DB)
    gen.add_argument("--workers", type=int, default=4)
    gen.add_argument("--resume", action="store_true")
    jud = sub.add_parser("judge")
    jud.add_argument("--output", type=Path, default=OUTPUT_V4)
    jud.add_argument("--workers", type=int, default=4)
    jud.add_argument("--resume", action="store_true")
    ana = sub.add_parser("analyze")
    ana.add_argument("--output", type=Path, default=OUTPUT_V4)
    args = parser.parse_args()
    if args.command == "prepare":
        result: Any = prepare(args.source, args.output)
    elif args.command == "generate":
        result = generate(args.output, args.kg_db, args.workers, args.resume)
    elif args.command == "judge":
        result = judge(args.output, args.workers, args.resume)
    else:
        result = analyze(cases_dir=CASES_DIR, output_dir=args.output)["integrity"]
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
