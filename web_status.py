"""Progress of a run root's configurations: runs (ok / failed), judged by both judges, audited, labelled.

Usage: python web_status.py [run root under experiments/high_temperature_hea_qwen35b, default loop_web]
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

E = Path(__file__).resolve().parent / "experiments" / "high_temperature_hea_qwen35b"
WEB = E / (sys.argv[1] if len(sys.argv) > 1 else "loop_web")


def count(path: Path) -> int:
    return sum(1 for _ in path.glob("PMC*.json")) if path.exists() else 0


def main() -> None:
    totals: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    print(f"{'configuration':38s} {'runs':>5s} {'ok':>5s} {'fail':>5s} {'gpt':>5s} {'deep':>5s} {'audit':>5s} {'label':>5s}")
    for method in sorted(p for p in WEB.iterdir() if (p / "runs").is_dir()):
        runs = [json.loads(p.read_text()) for p in sorted((method / "runs").glob("PMC*.json"))]
        ok = sum(r["status"] == "ok" for r in runs)
        for r in runs:
            if r["status"] != "ok":
                errors[(r.get("error") or "")[:90]] += 1
        row = {"runs": len(runs), "ok": ok, "fail": len(runs) - ok, "gpt": count(method / "judgments" / "gpt56"),
               "deep": count(method / "judgments" / "deepseek"), "audit": count(method / "audit"),
               "label": count(method / "labels")}
        totals.update(row)
        print(f"{method.name:38s} " + " ".join(f"{row[k]:5d}" for k in row))
    print(f"{'TOTAL':38s} " + " ".join(f"{totals[k]:5d}" for k in ("runs", "ok", "fail", "gpt", "deep", "audit", "label")))
    for error, n in errors.most_common(8):
        print(f"  {n:4d} x {error}")


if __name__ == "__main__":
    main()
