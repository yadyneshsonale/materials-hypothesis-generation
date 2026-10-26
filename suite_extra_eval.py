"""Experiment 32 (loop.md 15.1): DeepSeek cross-judge and target-free audit for the experiment 7, 9 and 11 frameworks.

Those frameworks have only the GPT-5.6 absolute judge. must_obey.md 6.7 requires the cross-judge and the audit on every
run, so this adds both with the payloads used by rubric_eval.py and hypo_loop.py:
- the judge sees the blinded hypothesis and cited evidence;
- the audit sees a target-free payload.

Units, under MATHG_RUN_ROOT:
- `eval_v3/runs`, all settings;
- `eval_critique/baseline_resample/runs`;
- `eval_v4_matkg/runs`. Its baseline runs are byte-identical copies of eval_v3 runs and reuse their outputs.
- `eval_critique/revisions/<arm>/`, the revised hypotheses.

Outputs:
- runs: `<dir>/judgments/deepseek/<id>.json` and `<dir>/audit/<id>.json`;
- revisions: `eval_critique/judgments/deepseek_<arm>/<id>.json` and `eval_critique/audit/<arm>/<id>.json`.
"""

from __future__ import annotations

import argparse
import json
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import llm_client as lc
from hypothesis_evidence_v2 import atomic_json
from stage_metrics import AUDIT_SYSTEM, CROSS_JUDGE, _validated_audit, assert_target_free
from temporal_eval_v3 import CASES_DIR, HYPOTHESIS_FIELDS, RUN_ROOT, _blind_candidate, load_cases
from temporal_hypothesis_benchmark import _SCORE_SYSTEM, _read_json, _validate_score


def units(root: Path = RUN_ROOT) -> list[dict[str, Any]]:
    """Every successful generation: its run-like record, output paths and, for copies, the source run file."""
    out: list[dict[str, Any]] = []
    for sub in ("eval_v3", "eval_critique/baseline_resample", "eval_v4_matkg"):
        base = root / sub
        for path in sorted((base / "runs").glob("PMC*.json")):
            run = _read_json(path)
            if run.get("status") != "ok":
                continue
            source = root / "eval_v3" / "runs" / path.name
            copy_of = (source if sub == "eval_v4_matkg" and source.exists()
                       and source.read_bytes() == path.read_bytes() else None)
            out.append({"id": f"{sub}/{path.stem}", "run": run, "copy_of": copy_of,
                        "deep": base / "judgments" / "deepseek" / path.name, "audit": base / "audit" / path.name})
    for arm_dir in sorted(p for p in (root / "eval_critique" / "revisions").glob("*") if p.is_dir()):
        for path in sorted(arm_dir.glob("PMC*.json")):
            rev = _read_json(path)
            if rev.get("status") != "ok":
                continue
            run = {"run_id": rev["run_id"], "paper_id": rev["paper_id"], "query": rev["query"],
                   "generation": rev["revised_generation"], "cited_evidence": rev["cited_evidence"]}
            out.append({"id": f"eval_critique/{arm_dir.name}/{path.stem}", "run": run, "copy_of": None,
                        "deep": root / "eval_critique" / "judgments" / f"deepseek_{arm_dir.name}" / path.name,
                        "audit": root / "eval_critique" / "audit" / arm_dir.name / path.name})
    return out


def judge_payload(run: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    generation, evidence = _blind_candidate(run)
    return {"query": run["query"], "hidden_target": case["hidden_target"], "generated_hypothesis": generation,
            "cited_evidence": evidence}


def audit_payload(run: dict[str, Any]) -> dict[str, Any]:
    payload = {"query": run["query"],
               "hypothesis": {k: run["generation"].get(k) for k in HYPOTHESIS_FIELDS if k in run["generation"]},
               "cited_evidence": [{"record_id": c["record_id"], "text": c["text"]} for c in run["cited_evidence"]]}
    assert_target_free(payload)
    return payload


def cross_judge(unit: dict[str, Any], case: dict[str, Any]) -> None:
    raw = lc.trapi_chat_json(CROSS_JUDGE["deployment"], _SCORE_SYSTEM,
                             json.dumps(judge_payload(unit["run"], case), ensure_ascii=False), max_tokens=8000,
                             token_field=CROSS_JUDGE["token_field"], temperature=CROSS_JUDGE["temperature"], retries=6)
    score = _validate_score(raw)
    atomic_json(unit["deep"], {"run_id": unit["run"]["run_id"], "judge": f"trapi:{CROSS_JUDGE['deployment']}",
                               "scores": score["scores"], "classification": score.get("classification", "")})


def audit(unit: dict[str, Any]) -> None:
    raw = lc.judge_chat_json(AUDIT_SYSTEM, json.dumps(audit_payload(unit["run"]), ensure_ascii=False),
                             max_tokens=16000)
    atomic_json(unit["audit"], {"run_id": unit["run"]["run_id"], "auditor": lc.judge_info(), **_validated_audit(raw)})


def run_stage(stage: str, workers: int, root: Path = RUN_ROOT) -> dict[str, int]:
    cases = {c["paper_id"]: c for c in load_cases(CASES_DIR, None)}
    key = "deep" if stage == "cross_judge" else "audit"
    todo = [u for u in units(root) if not u[key].exists()]
    copies = [u for u in todo if u["copy_of"] is not None]
    fresh = [u for u in todo if u["copy_of"] is None]
    counts = {"jobs": len(todo), "done": 0, "copied": 0, "failed": 0}
    with ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(cross_judge, u, cases[u["run"]["paper_id"]]) if key == "deep" else pool.submit(audit, u):
                   u for u in fresh}
        for future in as_completed(futures):
            try:
                future.result()
                counts["done"] += 1
            except Exception as error:  # noqa: BLE001 - logged; the next call retries
                counts["failed"] += 1
                print(f"[suite_extra_eval] {stage} {futures[future]['id']}: {type(error).__name__}: {str(error)[:200]}",
                      flush=True)
    for unit in copies:
        source = unit["copy_of"].parent.parent / ("judgments/deepseek" if key == "deep" else "audit") / unit["copy_of"].name
        if source.exists():
            unit[key].parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, unit[key])
            counts["copied"] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("cross_judge", "audit"))
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    print(args.stage, run_stage(args.stage, args.workers), flush=True)


if __name__ == "__main__":
    main()
