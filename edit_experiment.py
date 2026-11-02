"""Experiment 45 (loop.md 26.1): runner and analysis for the lever-preserving editor (E) and the domain context (D).

Stages (resumable; one process caps every model's calls with MATHG_MAX_PER_DEPLOYMENT):
  python edit_experiment.py generate [--workers N]    D on questions that do not name the alloy class and E on the
                                                       experiment-44 bases, then E on D
  python edit_experiment.py deepseek [--workers N]    DeepSeek reconstruction (hypo_loop cross_judge)
  python edit_experiment.py rq --rep R [--workers N]  research quality (rq_judge), DeepSeek, call R (1, 2, 3)
  python edit_experiment.py pairwise --judge J        target-free pairwise quality, both orders (deepseek, o1)
  python edit_experiment.py report                    loop_rx/analysis_edit.json and analysis_edit.md
GPT-5.6 judging and audits use hypo_loop.py judge / audit with MATHG_LOOP_ROOT=loop_rx.
"""

from __future__ import annotations

import rx_experiment as X  # noqa: I001 - first: it points MATHG_LOOP_ROOT at loop_rx before hypo_loop loads

import argparse  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import statistics  # noqa: E402
from collections import Counter, defaultdict  # noqa: E402
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: E402
from typing import Any  # noqa: E402

import edit_loop as EL  # noqa: E402
import hypo_loop as H  # noqa: E402
from hypothesis_evidence_v2 import atomic_json  # noqa: E402
from temporal_hypothesis_benchmark import _read_json  # noqa: E402

A, V, W, D, RQ = X.A, X.V, X.W, X.D, X.RQ
OUT = X.OUT
ARMS = EL.EDIT_ARMS
RQ.ROOTS.update({arm: "loop_rx" for arm in ARMS})
BASES = {"rx_base": {"E": "edit_rx_base", "D": "domain_rx_base", "DE": "domain_edit_rx_base"},
         "rx_r": {"E": "edit_rx_r", "D": "domain_rx_r", "DE": "domain_edit_rx_r"}}
PRIMARY = "rx_base"
VARIANTS = ("E", "D", "DE")
PAIRWISE = tuple((arms[v], base) for base, arms in BASES.items() for v in VARIANTS)
PAIR_JUDGES = ("deepseek", "o1")
DIMS = ("intervention_reconstruction", "condition_agreement", "mechanism_agreement", "outcome_agreement")
MPEA_EFFECT = re.compile(r"lattice distortion|sluggish diffusion|short[- ]range order|cocktail|mixing entropy|"
                         r"configurational entropy|high[- ]entropy effect|multi[- ]?principal[- ]element effect", re.I)
CAUSAL = re.compile(r"\bbecause\b|\bvia\b|\bthrough\b|\bby\b|\bdriven by\b|\bowing to\b|\bdue to\b", re.I)


def units() -> list[tuple[dict[str, Any], str]]:
    return X.units()


def named_units() -> dict[tuple[str, str], bool]:
    return {(c["paper_id"], lvl): EL.names_alloy_class(c["queries"][lvl]["text"]) for c, lvl in units()}


# ---------------------------------------------------------------- generation

def generate(workers: int) -> dict[str, Any]:
    named = named_units()
    out = {}
    phases = (("domain_rx_base", "domain_rx_r", "edit_rx_base", "edit_rx_r"), ("domain_edit_rx_base", "domain_edit_rx_r"))
    for number, phase in enumerate(phases, 1):
        jobs = []
        for case, level in units():
            for sample in H.SAMPLES:
                for arm in phase:
                    if arm.startswith("domain") and named[(case["paper_id"], level)]:
                        continue
                    if arm in EL.STAGE1:
                        stage1 = EL.STAGE1[arm][0]
                        first = OUT / stage1 / "runs" / f"{H.run_id(case['paper_id'], level, stage1, sample)}.json"
                        if not first.exists() or _read_json(first)["status"] != "ok":
                            continue
                    path = OUT / arm / "runs" / f"{H.run_id(case['paper_id'], level, arm, sample)}.json"
                    if path.exists() and _read_json(path)["status"] == "ok":
                        continue
                    if path.exists():
                        kept = OUT / arm / "failed_attempts" / path.name
                        kept.parent.mkdir(parents=True, exist_ok=True)
                        kept.write_text(path.read_text())
                    jobs.append((arm, case, level, sample, False))
        counts: Counter[str] = Counter()
        with ThreadPoolExecutor(workers) as pool:
            futures = [pool.submit(H.generate_one, *job) for job in jobs]
            for future in as_completed(futures):
                future.result()
                counts["done"] += 1
        out[f"phase{number}"] = {"jobs": len(jobs), **counts}
    return out


# ---------------------------------------------------------------- scores, composed per question

def runlevel(method: str, judge: str, metric: Any = A.recon) -> dict[tuple[str, str, int], Any]:
    """{(paper, level, sample): metric(scores)} for successful runs judged by "gpt" (GPT-5.6) or "deep"."""
    X._check_judge(judge)
    folder = "gpt56" if judge == "gpt" else "deepseek"
    out = {}
    for run in W.runs(OUT, method):
        if run.get("status") != "ok" or run["query_level"] not in W.LEVELS:
            continue
        path = OUT / method / "judgments" / folder / f"{run['run_id']}.json"
        if path.exists():
            out[(run["paper_id"], run["query_level"], int(run["sample"]))] = metric(_read_json(path)["scores"])
    return out


def sources(base: str, variant: str) -> tuple[str, str]:
    """(arm used on questions that name the alloy class, arm used on the others)."""
    arms = BASES[base]
    return {"base": (base, base), "E": (arms["E"], arms["E"]), "D": (base, arms["D"]),
            "DE": (arms["E"], arms["DE"]), "D_only": (arms["D"], arms["D"]),
            "DE_only": (arms["DE"], arms["DE"])}[variant]


def compose(base: str, variant: str, loader: Any) -> dict[tuple[str, str, int], Any]:
    named = named_units()
    first, second = sources(base, variant)
    a = loader(first)
    b = a if second == first else loader(second)
    out = {k: v for k, v in a.items() if named.get((k[0], k[1]))}
    out.update({k: v for k, v in b.items() if not named.get((k[0], k[1]))})
    return out


def per_paper(values: dict[tuple[str, str, int], float], keys: list[tuple[str, str, int]]) -> dict[str, float]:
    by: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for k in keys:
        by[k[0]][k[1]].append(values[k])
    return {p: statistics.fmean(statistics.fmean(v) for v in lv.values()) for p, lv in by.items()}


def contrast(new: dict[tuple[str, str, int], float], ref: dict[tuple[str, str, int], float],
             subset: str | None = None) -> dict[str, Any]:
    named = named_units()
    keys = sorted(set(new) & set(ref))
    if subset == "unnamed":
        keys = [k for k in keys if not named[(k[0], k[1])]]
    return {"runs": len(keys), **A.paired(per_paper(new, keys), per_paper(ref, keys))}


def recon_loader(judge: str) -> Any:
    return lambda method: runlevel(method, judge)


def rq_loader(k: int = 3) -> Any:
    def load(method: str) -> dict[tuple[str, str, int], float]:
        out = {}
        for item, x in RQ.load("runs", method, "deepseek", k).items():
            paper, level, _, sample = item.split("__")
            out[(paper, level, int(sample.lstrip("s")))] = x["rq"]
        return out
    return load


def family(base: str, loader: Any) -> list[dict[str, Any]]:
    ref = compose(base, "base", loader)
    items = [{"config": v, "vs": base, **contrast(compose(base, v, loader), ref)} for v in VARIANTS]
    return V.holm_family(items)


def decision(gpt: dict[str, Any], deep: dict[str, Any]) -> str:
    if not gpt.get("papers") or not deep.get("papers"):
        return "no data"
    if gpt["ci95"][0] > 0 and deep["diff"] > 0:
        return "raises the score"
    if gpt["ci95"][1] < 0 and deep["diff"] < 0:
        return "lowers the score"
    return "no detectable difference"


def subset_contrasts(base: str, judge: str) -> dict[str, Any]:
    """On the questions that do not name the alloy class: D and D+E against the base, and D+E against E."""
    load = recon_loader(judge)
    return {"D_vs_base": contrast(compose(base, "D", load), compose(base, "base", load), "unnamed"),
            "DE_vs_base": contrast(compose(base, "DE", load), compose(base, "base", load), "unnamed"),
            "DE_vs_E": contrast(compose(base, "DE", load), compose(base, "E", load), "unnamed")}


def dims(base: str, variant: str, judge: str) -> dict[str, float | None]:
    values = compose(base, variant, lambda m: runlevel(m, judge, metric=lambda s: s))
    return {d: W.A_mean([float(s[d]) for s in values.values()]) for d in DIMS}


def means(base: str, variant: str, loader: Any) -> float | None:
    values = compose(base, variant, loader)
    return W.A_mean(list(per_paper(values, sorted(values)).values())) if values else None


# ---------------------------------------------------------------- diagnostics

def words(text: Any) -> int:
    return len(str(text or "").split())


def edit_diagnostics(arm: str) -> dict[str, Any]:
    runs = [r for r in W.runs(OUT, arm) if r.get("status") == "ok"]
    if not runs:
        return {"runs": 0}
    stage1 = EL.STAGE1[arm][0]
    before_fields: dict[str, list[float]] = defaultdict(list)
    after_fields: dict[str, list[float]] = defaultdict(list)
    numbers: dict[str, Counter[str]] = {"before": Counter(), "after": Counter()}
    effects, causal = Counter(), Counter()
    attempts, changed = Counter(), Counter()
    for run in runs:
        edit = run["notes"]["edit"]
        draft = _read_json(OUT / stage1 / "runs" / f"{run['notes']['stage1']['run_id']}.json")["generation"]
        final = run["generation"]
        attempts[f"{len(edit['attempts'])} call(s), applied={edit['applied']}"] += 1
        for f in edit["attempts"][-1].get("changed", []) if edit["applied"] else []:
            changed[f] += 1
        for f in ("hypothesis", "intervention", "conditions", "structural_mediator", "mechanism",
                  "predicted_outcome"):
            before_fields[f].append(words(draft.get(f)))
            after_fields[f].append(words(final.get(f)))
        for when, key in (("before", "invented_numbers_before"), ("after", "invented_numbers_after")):
            for f, n in edit[key].items():
                numbers[when][f] += int(n > 0)
        effects["before"] += bool(MPEA_EFFECT.search(str(draft.get("mechanism", ""))))
        effects["after"] += bool(MPEA_EFFECT.search(str(final.get("mechanism", ""))))
        causal["before"] += bool(CAUSAL.search(str(draft.get("hypothesis", ""))))
        causal["after"] += bool(CAUSAL.search(str(final.get("hypothesis", ""))))
    n = len(runs)
    total = {w: statistics.fmean(sum(v[i] for v in fields.values()) for i in range(n))
             for w, fields in (("before", before_fields), ("after", after_fields))}
    return {"runs": n, "calls": dict(attempts), "fields_changed": {f: round(c / n, 3) for f, c in changed.items()},
            "invented_numbers_share": {w: {f: round(c / n, 3) for f, c in numbers[w].items()} for w in numbers},
            "mechanism_names_mpea_effect": {w: round(effects[w] / n, 3) for w in ("before", "after")},
            "hypothesis_states_causal_link": {w: round(causal[w] / n, 3) for w in ("before", "after")},
            "words": {f: [round(statistics.fmean(before_fields[f]), 1), round(statistics.fmean(after_fields[f]), 1)]
                      for f in before_fields},
            "words_total": [round(total["before"], 1), round(total["after"], 1)]}


def domain_diagnostics(base: str) -> dict[str, Any]:
    """Share of hypotheses on the unnamed questions that bring in a high-entropy alloy, base vs D."""
    named = named_units()
    out = {}
    for label, arm in (("base", base), ("D", BASES[base]["D"])):
        runs = [r for r in W.runs(OUT, arm) if r.get("status") == "ok" and not named[(r["paper_id"], r["query_level"])]]
        hits = [EL.names_alloy_class(f"{r['generation'].get('intervention', '')} "
                                     f"{r['generation'].get('material_initial_state', '')}") for r in runs]
        out[label] = {"runs": len(runs), "brings_in_alloy_class": D.share(hits)}
    return out


def pairwise_results(judge: str) -> dict[str, Any]:
    """Net preference for the new arm over its base (both orders agree = a win), composed like the scores."""
    named = named_units()
    per_cmp: dict[str, dict[tuple[str, str, int], float]] = {}
    for new, base in PAIRWISE:
        folder = OUT / "pairwise" / f"{new}__vs__{base}" / judge
        by: dict[str, dict[str, Any]] = defaultdict(dict)
        for path in sorted(folder.glob("*.json")) if folder.exists() else []:
            stem, order = path.stem.rsplit("__", 1)
            by[stem][order] = _read_json(path)
        vals = {}
        for stem, orders in by.items():
            if len(orders) == 2:
                paper, level, sample = stem.split("__")
                won = all(o["new_won"] for o in orders.values())
                lost = all(o["baseline_won"] for o in orders.values())
                vals[(paper, level, int(sample.lstrip("s")))] = 1.0 if won else -1.0 if lost else 0.0
        per_cmp[new] = vals
    out = {}
    for base, arms in BASES.items():
        composed = {"E": per_cmp.get(arms["E"], {}),
                    "D": {k: v for k, v in per_cmp.get(arms["D"], {}).items() if not named[(k[0], k[1])]},
                    "DE": {**{k: v for k, v in per_cmp.get(arms["E"], {}).items() if named[(k[0], k[1])]},
                           **{k: v for k, v in per_cmp.get(arms["DE"], {}).items() if not named[(k[0], k[1])]}}}
        items = []
        for variant, vals in composed.items():
            if not vals:
                continue
            keys = sorted(vals)
            pp = per_paper(vals, keys)
            items.append({"config": variant, "vs": base, "pairs": len(keys),
                          "new_wins": D.share([vals[k] == 1 for k in keys]),
                          "base_wins": D.share([vals[k] == -1 for k in keys]),
                          **A.paired(pp, {p: 0.0 for p in pp})})
        out[base] = V.holm_family(items)
    return out


def arm_summary(arm: str) -> dict[str, Any]:
    all_runs = W.runs(OUT, arm)
    ok = [r for r in all_runs if r.get("status") == "ok"]
    calls = [float(r["llm_calls"] + (r["notes"].get("stage1", {}).get("llm_calls") or 0)) for r in ok]
    return {"runs_ok": len(ok), "runs_failed": sum(r.get("status") != "ok" for r in all_runs),
            "failed_attempts": len(list((OUT / arm / "failed_attempts").glob("*.json"))),
            "deepseek_judged": X.judged_count(arm, "deep"), "gpt56_judged": X.judged_count(arm, "gpt"),
            "audits": len(list((OUT / arm / "audit").glob("*.json"))),
            "llm_calls_incl_stage1": W.A_mean(calls)}


def report() -> dict[str, Any]:
    deep, gpt = recon_loader("deep"), recon_loader("gpt")
    result: dict[str, Any] = {"arms": {a: arm_summary(a) for a in ARMS}, "families": {}, "subsets": {},
                              "means": {}, "dims": {}, "rq3": {}, "edit": {}, "domain": {}}
    for base in BASES:
        g, d = family(base, gpt), family(base, deep)
        for gi, di in zip(g, d):
            gi["decision"] = decision(gi, di)
        result["families"][base] = {"gpt56": g, "deepseek": d, "rq3": family(base, rq_loader(3))}
        result["subsets"][base] = {"gpt56": subset_contrasts(base, "gpt"), "deepseek": subset_contrasts(base, "deep")}
        result["means"][base] = {v: {"gpt56": means(base, v, gpt), "deepseek": means(base, v, deep),
                                     "rq3": means(base, v, rq_loader(3))} for v in ("base",) + VARIANTS}
        result["dims"][base] = {v: {"gpt56": dims(base, v, "gpt"), "deepseek": dims(base, v, "deep")}
                                for v in ("base",) + VARIANTS}
        result["edit"][base] = {v: edit_diagnostics(BASES[base][v]) for v in ("E", "DE")}
        result["domain"][base] = domain_diagnostics(base)
    result["pairwise"] = {j: pairwise_results(j) for j in PAIR_JUDGES}
    result["named_questions"] = Counter(named_units().values())
    result["leakage"] = X.leakage(ARMS)
    return result


def _f(x: Any, digits: int = 3) -> str:
    return "–" if x is None else f"{x:.{digits}f}" if isinstance(x, float) else str(x)


def _c(item: dict[str, Any]) -> str:
    if not item.get("papers"):
        return "no data"
    return (f"{item['diff']:+.3f} [{item['ci95'][0]:+.2f}, {item['ci95'][1]:+.2f}], {item['up']}/{item['down']} "
            f"papers, p {item['p']}" + (f", Holm {item['holm_p']}" if "holm_p" in item else ""))


def render(r: dict[str, Any]) -> str:
    named = r["named_questions"]
    L = ["# Experiment 45: a lever-preserving editor (E) and the programme's domain (D)", "",
         "Pre-registered in loop.md 26.1. GPT-5.6 reconstruction decides (CI above 0 and DeepSeek above 0); DeepSeek, "
         "research quality (RQ, mean of three DeepSeek calls) and target-free pairwise quality alongside. "
         f"Questions naming the alloy class: {named.get(True, 0)}; not naming it: {named.get(False, 0)}. "
         "D and D+E are composed: the base (or E) where the question names the class, the new arm elsewhere.", "",
         "## Runs", "", "| arm | ok | failed | failed attempts | DeepSeek judged | GPT-5.6 judged | audits | calls incl. "
         "stage 1 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for arm, s in r["arms"].items():
        L.append(f"| {arm} | {s['runs_ok']} | {s['runs_failed']} | {s['failed_attempts']} | {s['deepseek_judged']} | "
                 f"{s['gpt56_judged']} | {s['audits']} | {_f(s['llm_calls_incl_stage1'], 2)} |")
    for base in BASES:
        fam = r["families"][base]
        L += ["", f"## Base `{base}`" + (" (primary)" if base == PRIMARY else " (secondary)"), "",
              "| variant | GPT-5.6 mean | DeepSeek mean | RQ (3 calls) | GPT-5.6 vs base | DeepSeek vs base | "
              "RQ vs base | decision |", "|---|---:|---:|---:|---|---|---|---|"]
        m = r["means"][base]
        L.append(f"| base | {_f(m['base']['gpt56'])} | {_f(m['base']['deepseek'])} | {_f(m['base']['rq3'])} | – | – "
                 f"| – | – |")
        for g, d, q in zip(fam["gpt56"], fam["deepseek"], fam["rq3"]):
            v = g["config"]
            L.append(f"| {v} | {_f(m[v]['gpt56'])} | {_f(m[v]['deepseek'])} | {_f(m[v]['rq3'])} | {_c(g)} | {_c(d)} | "
                     f"{_c(q)} | {g.get('decision')} |")
        L += ["", "On the questions that do not name the alloy class:", "", "| contrast | GPT-5.6 | DeepSeek |",
              "|---|---|---|"]
        for key in ("D_vs_base", "DE_vs_base", "DE_vs_E"):
            L.append(f"| {key} | {_c(r['subsets'][base]['gpt56'][key])} | {_c(r['subsets'][base]['deepseek'][key])} |")
        L += ["", "Dimensions (GPT-5.6 / DeepSeek):", "", "| variant | intervention | conditions | mechanism | outcome |",
              "|---|---|---|---|---|"]
        for v, dd in r["dims"][base].items():
            L.append(f"| {v} | " + " | ".join(f"{_f(dd['gpt56'][k], 2)} / {_f(dd['deepseek'][k], 2)}" for k in DIMS)
                     + " |")
        L += ["", "Edit diagnostics:", "", "```", json.dumps(r["edit"][base], indent=1), "```",
              "Domain diagnostics:", "", "```", json.dumps(r["domain"][base], indent=1), "```"]
    L += ["", "## Target-free pairwise quality (net preference for the variant; both orders must agree)", ""]
    for judge, by_base in r["pairwise"].items():
        for base, items in by_base.items():
            for it in items:
                L.append(f"- {judge}, {it['config']} vs {base}: {_c(it)}; pairs {it['pairs']}, variant wins "
                         f"{it['new_wins']}, base wins {it['base_wins']}")
    L += ["", "## Leakage", "", json.dumps(r["leakage"]), ""]
    return "\n".join(L)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("generate", "deepseek", "rq", "pairwise", "report"))
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--rep", type=int, default=1)
    parser.add_argument("--judge", default="deepseek", choices=PAIR_JUDGES)
    args = parser.parse_args()
    if args.stage == "generate":
        print(generate(args.workers))
    elif args.stage == "deepseek":
        print(H.cross_judge_stage(args.workers, list(ARMS)))
    elif args.stage == "rq":
        items = RQ.run_items(list(ARMS))
        if args.rep > 1:
            items = [(RQ.rep_kind(k, args.rep), n, i, d) for k, n, i, d in items]
        print(RQ.run_stage(items, "deepseek", args.workers))
    elif args.stage == "pairwise":
        print(X.pairwise_stage(args.workers, args.judge, PAIRWISE))
    else:
        result = report()
        atomic_json(OUT / "analysis_edit.json", result)
        (OUT / "analysis_edit.md").write_text(render(result))
        print(render(result))


if __name__ == "__main__":
    main()
