"""Helper: process remaining judge or audit jobs in reverse order, skipping finished units, to speed up a run
that is already in progress. Results are identical in form to the main stage; duplicates at the meeting point
simply overwrite with an equivalent judgment."""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor

import llm_client as lc
import rubric_eval as rx
from stage_metrics import AUDIT_SYSTEM, _validated_audit, assert_target_free
from temporal_eval_v3 import HYPOTHESIS_FIELDS, judge_absolute


def main(stage: str, workers: int) -> None:
    runs = [r for r in rx.load_runs().values() if r["status"] == "ok"][::-1]
    out = rx.OUT / ("audit" if stage == "audit" else "judgments/gpt56")

    def job(run: dict) -> int:
        path = out / f"{run['run_id']}.json"
        if path.exists():
            return 0
        try:
            if stage == "audit":
                payload = {"query": run["query"],
                           "hypothesis": {k: run["generation"].get(k) for k in HYPOTHESIS_FIELDS if k in run["generation"]},
                           "cited_evidence": [{"record_id": c["record_id"], "text": c["text"]} for c in run["cited_evidence"]]}
                assert_target_free(payload)
                raw = lc.judge_chat_json(AUDIT_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=16000)
                if not path.exists():
                    rx.atomic_json(path, {"run_id": run["run_id"], "auditor": lc.judge_info(), **_validated_audit(raw)})
            else:
                judgment = judge_absolute(run, rx.cases()[run["paper_id"]])
                if not path.exists():
                    rx.atomic_json(path, judgment)
            return 1
        except Exception:  # noqa: BLE001 - the main stage's resume pass retries anything missing
            return 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        done = sum(pool.map(job, runs))
    print(json.dumps({"stage": stage, "completed_by_helper": done}))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
