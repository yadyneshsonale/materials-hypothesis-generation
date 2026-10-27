"""Experiment 36 (loop.md 17.2, item 6): copies the suite's closed-book baselines from experiment 21 into the web run
root. Their inputs do not change with web search, so they are not re-run. Knowledge-first refines the fixed closed book
and ensemble selection uses it as a candidate. Each copy records its source; its judgments and audits are copied
with it.

Usage: python web_suite_prepare.py [--source DIR] [--target DIR]
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from hypothesis_evidence_v2 import atomic_json
from temporal_eval_v3 import EXPERIMENT_DIR
from temporal_hypothesis_benchmark import _read_json

COPIES = (  # (framework directory, run file pattern, judgment and audit directories copied along)
    ("eval_v3", "*__closed_book.json", ("judgments/absolute", "judgments/deepseek", "audit")),
    ("rubric_eval", "*__closed_book__s*.json", ("judgments/gpt56", "judgments/deepseek", "audit")),
    ("improvements", "*__closed_book_fixed__s*.json", ("judgments/gpt56", "judgments/deepseek", "audit")),
)


def prepare(source: Path, target: Path) -> dict[str, int]:
    counts = {"runs": 0, "evaluations": 0}
    for framework, pattern, extras in COPIES:
        for path in sorted((source / framework / "runs").glob(pattern)):
            dest = target / framework / "runs" / path.name
            if not dest.exists():
                run = _read_json(path)
                run["copied_from"] = str(path.relative_to(EXPERIMENT_DIR))
                atomic_json(dest, run)
                counts["runs"] += 1
            for extra in extras:
                origin = source / framework / extra / path.name
                copy = target / framework / extra / path.name
                if origin.exists() and not copy.exists():
                    copy.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(origin, copy)
                    counts["evaluations"] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--source", type=Path, default=EXPERIMENT_DIR / "rerun_v3")
    parser.add_argument("--target", type=Path, default=EXPERIMENT_DIR / "rerun_web")
    args = parser.parse_args()
    print(prepare(args.source, args.target))


if __name__ == "__main__":
    main()
