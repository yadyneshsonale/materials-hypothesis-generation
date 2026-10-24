"""Memorisation probe: does a generator already know the held-out papers?

Publication-date cutoffs only protect a benchmark if the generator's training data ends before the held-out papers
(MatDesign, MOOSE-Chem, IdeaBench, ResearchBench all rely on this). Nothing had checked the old generator,
Qwen3.5-35B-A3B (released February 2026). This probe gives each generator only the held-out paper's title and
year, asks what the paper did and found, and has GPT-5.6 score the recall against the hidden target. A model that
has not seen the paper can only guess from the title, so the probe also runs the pre-cutoff generator used for the
rerun (Llama-3.3-70B, knowledge cutoff December 2023) as a control. Titles reveal part of the topic, so what
matters is the difference between models, especially recall of details the title does not contain.
"""

from __future__ import annotations

import json
import os
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests

import llm_client as lc
import rubric_eval as rx
from hypothesis_evidence_v2 import atomic_json
from temporal_eval_v3 import EXPERIMENT_DIR

OUT = EXPERIMENT_DIR / "benchmark_v3" / "memorisation_probe"
SAMPLES = (1, 2)
PROBE_SYSTEM = (
    "Answer from your own memory only. You will be given the title and year of a published materials-science "
    "paper. Say whether you remember this specific paper, and describe what it did and found: the starting material, "
    "the intervention or method, the resulting structure, the mechanism, and the main quantitative results. If you "
    "do not remember the paper, say so and give your best guess, marked as a guess. Return JSON {\"remembers\": "
    "true|false, \"starting_material\": str, \"intervention\": str, \"structure\": str, \"mechanism\": str, "
    "\"results\": str}."
)
SCORE_SYSTEM = (
    "You compare a model's recollection of a paper with the paper's actual result. Score each dimension 0 to 2: "
    "0 = absent or wrong, 1 = generic or only what the title states, 2 = specific and correct beyond what the title "
    "states. Dimensions: intervention, structure, mechanism, quantitative_results (numbers close to the actual "
    "values). The paper title is given so you can tell what the title already reveals. Return JSON "
    "{\"intervention\": int, \"structure\": int, \"mechanism\": int, \"quantitative_results\": int, \"note\": str}."
)
MODELS = {
    "qwen3.5-35b-a3b": {"kind": "local"},
    "llama-3.3-70b": {"kind": "trapi", "deployment": "Llama-3.3-70B-Instruct_5"},
}


def ask(model: str, title: str, year: str) -> dict[str, Any]:
    user = json.dumps({"title": title, "year": year}, ensure_ascii=False)
    if MODELS[model]["kind"] == "trapi":
        return lc.trapi_chat_json(MODELS[model]["deployment"], PROBE_SYSTEM, user, max_tokens=1500, temperature=0.2)
    body = {"model": "Qwen3.5-35B-A3B-Q4_K_M.gguf", "max_tokens": 1500, "temperature": 0.2,
            "messages": [{"role": "system", "content": PROBE_SYSTEM}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"}, "chat_template_kwargs": {"enable_thinking": False}}
    response = requests.post(os.environ.get("QWEN_URL", "http://127.0.0.1:8000/v1") + "/chat/completions",
                             json=body, timeout=600)
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


def probe_one(paper_id: str, model: str, sample: int) -> dict[str, Any]:
    path = OUT / "runs" / f"{paper_id}__{model}__s{sample}.json"
    if path.exists():
        return json.loads(path.read_text())
    meta = rx.metadata()[paper_id]
    case = rx.cases()[paper_id]
    recollection = ask(model, str(meta["title"]), str(case["publication_date"])[:4])
    target = {k: case["hidden_target"].get(k) for k in ("material_initial_state", "intervention",
                                                         "structural_mediator", "mechanism", "actual_result")}
    score = lc.judge_chat_json(SCORE_SYSTEM, json.dumps({"title": meta["title"], "actual": target,
                                                         "recollection": recollection}, ensure_ascii=False),
                               max_tokens=4000)
    record = {"paper_id": paper_id, "model": model, "sample": sample, "title": meta["title"],
              "recollection": recollection, "score": score}
    atomic_json(path, record)
    return record


def main() -> None:
    jobs = [(pid, m, s) for pid in sorted(rx.cases()) for m in MODELS for s in SAMPLES]
    with ThreadPoolExecutor(6) as pool:
        records = list(pool.map(lambda j: probe_one(*j), jobs))
    dims = ("intervention", "structure", "mechanism", "quantitative_results")
    summary = {}
    for model in MODELS:
        rs = [r for r in records if r["model"] == model]
        summary[model] = {
            "claims_to_remember": round(statistics.fmean(bool(r["recollection"].get("remembers")) for r in rs), 3),
            **{d: round(statistics.fmean(int(r["score"].get(d, 0)) for r in rs), 3) for d in dims},
            "specific_recall_any_dim": round(statistics.fmean(
                any(int(r["score"].get(d, 0)) == 2 for d in dims) for r in rs), 3),
            "per_paper_total": {pid: round(statistics.fmean(sum(int(r["score"].get(d, 0)) for d in dims)
                                                           for r in rs if r["paper_id"] == pid), 2)
                                for pid in sorted(rx.cases())}}
    atomic_json(OUT / "summary.json", summary)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
