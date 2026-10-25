"""Round-3 failure analysis (loop.md section 11.2): where does the incumbent (writer_only_b_o3mini) lose points on
the 24-paper development set dev3 (dev + the spent test and test2 splits)? Target-aware, analysis only.

  A. Dimension means by split and gap type, for the incumbent and two references.
  B. Class hit (GPT-5.6 lever label >= 1) and the dimension means given a hit or a miss.
  C. Regime anchoring: does the hypothesis's conditions field repeat a quantity the question states (temperature,
     time, stress, strain rate, composition), and does that predict condition agreement? Lexical, target-free.
  D. Error mix of the judges' fatal errors (experiment-12 coder, GPT-5.6) for the incumbent.
Output: loop/failure_r3.json.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import hypo_loop as H
import llm_client as lc
from failure_analysis import CODER_SYSTEM, ERROR_CATEGORIES, validate_labels
from hypothesis_evidence_v2 import atomic_json

INCUMBENT = "writer_only_b_o3mini"
REFERENCES = ("closed_book_o3mini", "trend_ground_b_o3mini", "closed_book")
DIMS = ("intervention_reconstruction", "condition_agreement", "mechanism_agreement", "outcome_agreement")
QUANTITY = re.compile(r"(\d[\d.,]*)\s*(?:–|-|to)?\s*(?:\d[\d.,]*)?\s*(°\s?C|K\b|MPa|GPa|h\b|hours?|min|s[−-]1|"
                      r"at\.?\s?%|wt\.?\s?%|nm|µm|um)", re.IGNORECASE)


def quantities(text: str) -> set[str]:
    return {f"{m.group(1).replace(',', '')}{m.group(2).replace(' ', '').lower()}" for m in QUANTITY.finditer(text)}


def mean(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 3) if values else None


def gap_of(case: dict[str, Any]) -> str:
    return str((case.get("gap") or {}).get("gap_type") or "design")


def code_errors(rows: list[dict[str, Any]], workers: int = 3) -> dict[str, list[str]]:
    path = H.OUT / "failure_r3_codes.json"
    done: dict[str, list[str]] = json.loads(path.read_text()) if path.exists() else {}

    def job(row: dict[str, Any]) -> tuple[str, list[str]]:
        errors = [str(e) for e in row["gpt"].get("fatal_errors", [])][:8]
        if not errors:
            return row["run"]["run_id"], []
        raw = lc.judge_chat_json(CODER_SYSTEM, json.dumps({"errors": [{"index": i, "text": e} for i, e in
                                                                     enumerate(errors)]}, ensure_ascii=False),
                                 max_tokens=3000, retries=12)
        return row["run"]["run_id"], validate_labels(raw, len(errors))

    todo = [r for r in rows if r["run"]["run_id"] not in done]
    with ThreadPoolExecutor(workers) as pool:
        for rid, labels in pool.map(job, todo):
            done[rid] = labels
    atomic_json(path, dict(sorted(done.items())))
    return done


def main() -> None:
    cases = H.cases()
    rows = [r for r in H.load_scored() if r["run"]["split"] in H.SPLITS["dev3"] and r["gpt"]
            and r["run"]["method"] in (INCUMBENT, *REFERENCES)]
    out: dict[str, Any] = {"dev3_papers": len({r["run"]["paper_id"] for r in rows})}
    table: dict[str, Any] = {}
    for m in (INCUMBENT, *REFERENCES):
        rs = [r for r in rows if r["run"]["method"] == m]
        block: dict[str, Any] = {"runs": len(rs)}
        for key, group in (("split", lambda r: r["run"]["split"]), ("gap", lambda r: gap_of(cases[r["run"]["paper_id"]]))):
            by: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for r in rs:
                by[group(r)].append(r)
            block[key] = {g: {"n": len(v), "recon": mean([H.recon(r["gpt"]["scores"]) for r in v]),
                              **{d[:4]: mean([r["gpt"]["scores"][d] for r in v]) for d in DIMS},
                              "class_hit": mean([1.0 if r["label"]["lever_match"] >= 1 else 0.0 for r in v
                                                 if r["label"]])}
                          for g, v in sorted(by.items())}
        hit = [r for r in rs if r["label"] and r["label"]["lever_match"] >= 1]
        miss = [r for r in rs if r["label"] and r["label"]["lever_match"] == 0]
        block["given_hit"] = {d[:4]: mean([r["gpt"]["scores"][d] for r in hit]) for d in DIMS} | {"n": len(hit)}
        block["given_miss"] = {d[:4]: mean([r["gpt"]["scores"][d] for r in miss]) for d in DIMS} | {"n": len(miss)}
        anchored, unanchored = [], []
        for r in rs:
            asked = quantities(r["run"]["query"])
            if not asked:
                continue
            said = quantities(" ".join(str(r["run"]["generation"].get(k, "")) for k in ("conditions", "boundary",
                                                                                         "hypothesis")))
            (anchored if asked & said else unanchored).append(r["gpt"]["scores"]["condition_agreement"])
        block["regime_anchoring"] = {"units_with_stated_quantities": len(anchored) + len(unanchored),
                                     "anchored_share": mean([1.0] * len(anchored) + [0.0] * len(unanchored)),
                                     "condition_if_anchored": mean(anchored),
                                     "condition_if_not": mean(unanchored)}
        table[m] = block
    out["table"] = table
    inc = [r for r in rows if r["run"]["method"] == INCUMBENT]
    codes = code_errors(inc)
    mix = Counter(c for r in inc for c in codes.get(r["run"]["run_id"], []))
    total = sum(mix.values()) or 1
    out["error_mix_incumbent"] = {k: round(mix[k] / total, 3) for k in ERROR_CATEGORIES if mix[k]}
    out["fatal_errors_per_run"] = mean([len(codes.get(r["run"]["run_id"], [])) for r in inc])
    atomic_json(H.OUT / "failure_r3.json", out)
    print(json.dumps(out, indent=1)[:6000])


if __name__ == "__main__":
    main()
