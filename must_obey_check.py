"""Automated checks for must_obey.md. Run before reporting any result:

    python must_obey_check.py <run_dir> [<run_dir> ...] [--loop]

A run directory has `runs/*.json` (any of this repository's run formats) and, optionally, `judgments/` and
`audit/`. The check fails (exit code 1) when a rule is broken. It warns on flags that need reporting:
- query-facing model not on the pre-cutoff list, or its cutoff not before the case date (section 2);
- query text differs from the frozen benchmark_v3 query (section 3);
- non-zero leakage counters in a run's audit (section 4);
- missing GPT-5.6 / DeepSeek judgments or target-free audits for successful runs (section 6);
- with --loop: test-split runs not marked final, or no proof that the payload was asserted target-free (5, 6.5).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
BENCHMARKS = {"v3": ROOT / "experiments" / "high_temperature_hea_qwen35b" / "benchmark_v3" / "cases",
              "v3.1": ROOT / "experiments" / "high_temperature_hea_qwen35b" / "benchmark_v3_1" / "cases"}
CURRENT = "v3.1"
CASES = BENCHMARKS[CURRENT]

# Documented knowledge cutoffs (vendor documentation; sources in loop.md). Months are taken at their last day.
MODEL_CUTOFFS = {
    "Llama-3.3-70B-Instruct_5": "2023-12-31",
    "gcr-llama-31-8b-instruct": "2023-12-31",
    "gpt-4o_2024-11-20": "2023-10-01",
    "gpt-4o-mini_2024-07-18": "2023-10-01",
    "o1_2024-12-17": "2023-10-01",
    "o3-mini_2025-01-31": "2023-10-01",
}
LEAK_COUNTERS = ("temporal_violations", "test_paper_leaks", "family_leaks", "target_doi_or_title_leaks",
                 "invalid_citations", "unknown_record_ids")
MARGIN_DAYS = 31


def deployment(identity: str) -> str:
    """'trapi:o3-mini_2025-01-31' -> 'o3-mini_2025-01-31'; 'openai:Qwen...' -> 'Qwen...'."""
    return str(identity).split(":", 1)[-1].strip()


def frozen_queries(cases_dir: Path = CASES) -> dict[tuple[str, str], dict[str, Any]]:
    out = {}
    for path in sorted(cases_dir.glob("PMC*.json")):
        case = json.loads(path.read_text())
        for level, query in case["queries"].items():
            out[(case["paper_id"], level)] = {
                "sha256": hashlib.sha256(query["text"].encode("utf-8")).hexdigest(), "date": case["publication_date"],
                "split": "test" if case["split"] == "test" else "dev"}
    return out


def query_facing_models(run: dict[str, Any]) -> dict[str, str]:
    models = dict(run.get("models") or {})
    if run.get("generator"):
        models.setdefault("generator", run["generator"])
    return models


def judged(run_dir: Path, run_id: str) -> dict[str, bool]:
    j = run_dir / "judgments"
    return {"gpt56": (j / "gpt56" / f"{run_id}.json").exists() or (j / "absolute" / f"{run_id}.json").exists(),
            "deepseek": (j / "deepseek" / f"{run_id}.json").exists(),
            "audit": (run_dir / "audit" / f"{run_id}.json").exists()}


def check(run_dir: Path, loop: bool = False, require_cross: bool = True, bench: str = CURRENT) -> dict[str, Any]:
    queries = frozen_queries(BENCHMARKS[bench])
    failures: list[str] = []
    warnings: list[str] = []
    counts = {"runs": 0, "ok": 0, "failed": 0}
    margin_flags: set[str] = set()
    for path in sorted((run_dir / "runs").glob("PMC*.json")):
        run = json.loads(path.read_text())
        rid = run.get("run_id", path.stem)
        counts["runs"] += 1
        key = (run.get("paper_id"), run.get("query_level"))
        frozen = queries.get(key)
        if frozen is None:
            failures.append(f"{rid}: unknown case/level {key}")
            continue
        if hashlib.sha256(str(run.get("query", "")).encode("utf-8")).hexdigest() != frozen["sha256"]:
            failures.append(f"{rid}: query differs from frozen benchmark {bench} text")
        case_date = date.fromisoformat(frozen["date"])
        for role, identity in query_facing_models(run).items():
            name = deployment(identity)
            cutoff = MODEL_CUTOFFS.get(name)
            if cutoff is None:
                failures.append(f"{rid}: {role} model {name!r} is not on the pre-cutoff list")
                continue
            gap = (case_date - date.fromisoformat(cutoff)).days
            if gap <= 0:
                failures.append(f"{rid}: {role} model {name} cutoff {cutoff} is not before case date {case_date}")
            elif gap < MARGIN_DAYS:
                margin_flags.add(f"{run['paper_id']} is {gap} days after {name}'s cutoff")
        audit = run.get("audit") or {}
        for counter in LEAK_COUNTERS:
            if int(audit.get(counter, 0) or 0) != 0:
                failures.append(f"{rid}: audit.{counter} = {audit[counter]}")
        if loop:
            if frozen["split"] == "test" and not run.get("final"):
                failures.append(f"{rid}: test-split run not marked final (pre-register finals in loop.md)")
            if run.get("status") == "ok" and run.get("target_free_asserted") is not True:
                failures.append(f"{rid}: no proof that query-facing payloads were asserted target-free")
        if run.get("status") == "ok":
            counts["ok"] += 1
            have = judged(run_dir, rid)
            if not have["gpt56"]:
                failures.append(f"{rid}: missing GPT-5.6 judgment")
            if require_cross and not have["deepseek"]:
                warnings.append(f"{rid}: missing DeepSeek cross-judgment")
            if require_cross and not have["audit"]:
                warnings.append(f"{rid}: missing target-free audit")
        else:
            counts["failed"] += 1
    if counts["failed"]:
        warnings.append(f"{counts['failed']} failed run(s): report them, do not drop them")
    warnings += sorted(margin_flags)
    return {"run_dir": str(run_dir), **counts, "passed": not failures, "failures": failures, "warnings": warnings}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("run_dirs", nargs="+", type=Path)
    parser.add_argument("--loop", action="store_true", help="also apply the method-development rules")
    parser.add_argument("--no-cross", action="store_true", help="do not require DeepSeek judgments and audits")
    parser.add_argument("--bench", choices=sorted(BENCHMARKS), default=CURRENT, help="frozen query version")
    args = parser.parse_args()
    all_passed = True
    for run_dir in args.run_dirs:
        result = check(run_dir, loop=args.loop, require_cross=not args.no_cross, bench=args.bench)
        all_passed &= result["passed"]
        status = "PASS" if result["passed"] else "FAIL"
        print(f"[{status}] {run_dir}: {result['runs']} runs, {result['ok']} ok, {result['failed']} failed")
        for line in result["failures"][:20]:
            print(f"  FAIL  {line}")
        if len(result["failures"]) > 20:
            print(f"  ... {len(result['failures']) - 20} more failures")
        warnings = result["warnings"]
        for line in warnings[:8]:
            print(f"  warn  {line}")
        if len(warnings) > 8:
            print(f"  ... {len(warnings) - 8} more warnings")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
