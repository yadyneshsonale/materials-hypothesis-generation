"""Tests for the propose-critique-decide method (experiment 37, loop.md 18.1)."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import hypo_loop as H
import loop_methods as LM
from temporal_hypothesis_benchmark import RetrievalRecord

CASE = {"paper_id": "PMCT", "publication_date": "2024-06-01", "split": "validation",
        "queries": {"broad": {"text": "Improve the oxidation resistance of a refractory alloy."},
                    "problem_constrained": {"text": "Improve the oxidation resistance of cast HfNbTaTiZr at 1000 C."},
                    "expert_context": {"text": "Earlier work tried aluminide coatings; improve oxidation resistance."}},
        "hidden_target": {"intervention": "Ink-extrusion printing followed by a slurry silicide coating cured in vacuum",
                          "mechanism": "a self-healing mixed oxide forms in the silicide coating and blocks oxygen",
                          "material_initial_state": "HfNbTaTiZr"}}


def idea(n: int, word: str) -> dict:
    return {"material_system": "cast HfNbTaTiZr", "intervention": f"{word} coating applied by pack cementation",
            "conditions": "air, 1000 C, 100 h", "structural_mediator": f"{word} oxide scale",
            "mechanism": f"a dense {word} oxide blocks oxygen ingress", "predicted_outcome": "lower mass gain",
            "why_it_addresses_the_question": "it protects the surface", "supporting_record_ids": [f"card{n}", "bogus"]}


def pool(kind: str) -> list[RetrievalRecord]:
    words = ("silicide", "aluminide", "chromia", "zirconia")
    if kind == "card":
        return [RetrievalRecord(f"card{i}", f"P{i}", "2020-01-01", "web:card", f"oxidation resistance alloy {w} " * 60,
                                {"source": "web"}) for i, w in enumerate(words)]
    return [RetrievalRecord(f"pas{i}_{j}", f"P{i}", "2020-01-01", "web:Results", f"{w} coating oxide scale " * 80,
                            {"source": "web"}) for i, w in enumerate(words) for j in range(6)]


class Responder:
    """Fake model: answers each role with a fixed, valid JSON and records every payload."""

    def __init__(self, k: int = 4, decision_cites: str | None = None):
        self.calls: list[tuple[str, str, dict]] = []
        self.k = k
        self.decision_cites = decision_cites

    def __call__(self, role, model, system, payload, max_out=None):
        self.calls.append((role, model, payload))
        if role == "proposer":
            return {"ideas": [idea(n, w) for n, w in enumerate(("silicide", "aluminide", "chromia", "zirconia"))][:self.k]}
        if role == "critic":  # the aluminide idea (the proposer's I2) is the only strong one
            return {"critiques": [{"id": d["id"], "verdict": "strong" if "aluminide" in d["intervention"]
                                   else "Viable with changes", "fix": "thicker coating",
                                   "evidence_ids": ["pas0_0", "nope"]} for d in payload["directions"]]}
        hypothesis = {"hypothesis": "A silicide coating protects cast HfNbTaTiZr.", "intervention": "silicide coating",
                      "mechanism": "oxide scale", "supporting_evidence_ids": [self.decision_cites] if self.decision_cites
                      else [], "conflicting_evidence_ids": [], "extra_field": "dropped"}
        if role == "decider":
            first = payload["directions"][0]["id"]
            return {"decision": {"chosen_ids": [first], "mode": "adopt_with_fix", "rationale": "best fit"}, **hypothesis}
        return hypothesis


def run(method: str, responder: Responder) -> tuple[H.Harness, dict]:
    h = H.Harness(CASE, "problem_constrained", 1)
    with patch.object(h, "ask", side_effect=responder), \
            patch.object(h, "pool", side_effect=lambda representation: pool(representation)):
        out = H.METHODS[method](h)
    return h, out


class RegistrationTests(unittest.TestCase):
    def test_sixteen_configurations_are_registered(self) -> None:
        self.assertEqual(len(LM.PCD_CONFIGS), 16)
        for flags in LM.PCD_WEB:
            self.assertIn(f"pcd_{flags}_o3mini", H.METHODS)
        for name in ("pcd_nocritic_none_o3mini", "pcd_nodecider_PCD_o3mini", "pcd_k1_PCD_o3mini", "pcd_PCD_llama"):
            self.assertIn(name, H.METHODS)


class ParsingTests(unittest.TestCase):
    def test_ideas_need_intervention_and_mechanism_and_keep_only_known_records(self) -> None:
        raw = {"ideas": [{"intervention": "", "mechanism": "x"}, idea(0, "silicide"), idea(1, "aluminide"),
                         idea(2, "chromia")]}
        ideas = LM.parse_ideas(raw, 2, {"card0"})
        self.assertEqual([i["id"] for i in ideas], ["I1", "I2"])
        self.assertEqual(ideas[0]["supporting_record_ids"], ["card0"])
        self.assertEqual(ideas[1]["supporting_record_ids"], [])
        with self.assertRaises(ValueError):
            LM.parse_ideas({"ideas": []}, 4, set())

    def test_critiques_normalise_verdicts_and_mark_missing_ones(self) -> None:
        ideas = [{**i, "label": "ABC"[n]} for n, i in
                 enumerate(LM.parse_ideas({"ideas": [idea(0, "a"), idea(1, "b"), idea(2, "c")]}, 3, set()))]
        raw = {"critiques": [{"id": "A", "verdict": "Viable with changes", "evidence_ids": ["r1", "x"]},
                             {"id": "I9", "verdict": "strong"}, {"id": "C", "verdict": "excellent"}]}
        out = LM.parse_critiques(raw, ideas, {"r1"})
        self.assertEqual([c["verdict"] for c in out], ["viable_with_changes", "not_reviewed", "not_stated"])
        self.assertEqual(out[0]["evidence_ids"], ["r1"])
        with self.assertRaises(ValueError):
            LM.parse_critiques({"critiques": [{"id": "I9"}]}, ideas, set())

    def test_rule_choice_takes_best_verdict_then_the_proposers_earlier_idea(self) -> None:
        ideas = [{"id": "I3", "label": "A"}, {"id": "I1", "label": "B"}, {"id": "I2", "label": "C"}]  # shuffled
        self.assertEqual(LM.rule_choice(ideas, [{"id": "A", "verdict": "strong"}, {"id": "B", "verdict": "weak"},
                                                {"id": "C", "verdict": "strong"}])["id"], "I2")
        self.assertEqual(LM.rule_choice(ideas, [{"id": "A", "verdict": "weak"}, {"id": "B", "verdict": "weak"},
                                                {"id": "C", "verdict": "not_reviewed"}])["id"], "I1")

    def test_presentation_is_a_seeded_shuffle_with_neutral_labels(self) -> None:
        ideas = LM.parse_ideas({"ideas": [idea(n, w) for n, w in enumerate("abcd")]}, 4, set())
        orders = set()
        for sample in (1, 2, 3, 4, 5, 6):
            shown = LM.present(H.Harness(CASE, "broad", sample), ideas)
            self.assertEqual([i["label"] for i in shown], ["A", "B", "C", "D"])
            self.assertEqual(sorted(i["id"] for i in shown), ["I1", "I2", "I3", "I4"])
            orders.add(tuple(i["id"] for i in shown))
        self.assertGreater(len(orders), 1)
        again = LM.present(H.Harness(CASE, "broad", 1), ideas)
        self.assertEqual([i["id"] for i in again], [i["id"] for i in LM.present(H.Harness(CASE, "broad", 1), ideas)])


class EvidenceTests(unittest.TestCase):
    def test_budget_record_limit_one_per_paper_and_exclusion(self) -> None:
        h = H.Harness(CASE, "problem_constrained", 1)
        with patch.object(h, "pool", side_effect=lambda representation: pool(representation)):
            cards = LM.pcd_evidence(h, "silicide oxidation", "card", 16000, 1600, one_per_paper=True)
            small = LM.pcd_evidence(h, "silicide coating", "text_chunks", 4000, 1600, exclude=frozenset({"pas0_0"}))
        self.assertEqual(len({r.paper_id for r in cards}), len(cards))
        self.assertEqual(cards[0].record_id, "card0")
        self.assertNotIn("pas0_0", [r.record_id for r in small])
        self.assertLessEqual(sum(min(len(r.text), 1600) for r in small), 4000)
        self.assertLessEqual(len(small), 6)
        self.assertTrue(all(r.record_id in h.seen for r in cards + small))

    def test_each_idea_gets_its_own_share_without_duplicates(self) -> None:
        h = H.Harness(CASE, "problem_constrained", 1)
        ideas = [{**i, "label": "AB"[n]} for n, i in enumerate(
            LM.parse_ideas({"ideas": [idea(n, w) for n, w in enumerate(("silicide", "aluminide"))]}, 2, set()))]
        with patch.object(h, "pool", side_effect=lambda representation: pool(representation)):
            ev = LM.pcd_idea_evidence(h, ideas)
        ids = [r.record_id for recs in ev.values() for r in recs]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all("silicide" in r.text for r in ev["A"]))
        self.assertTrue(all("aluminide" in r.text for r in ev["B"]))
        self.assertTrue(all(sum(min(len(r.text), 1600) for r in recs) <= 8000 for recs in ev.values()))


class PipelineTests(unittest.TestCase):
    def test_no_web_runs_three_roles_without_evidence(self) -> None:
        responder = Responder()
        h, out = run("pcd_none_o3mini", responder)
        self.assertEqual([c[0] for c in responder.calls], ["proposer", "critic", "decider"])
        self.assertNotIn("earlier_papers", responder.calls[0][2])
        self.assertNotIn("evidence_by_direction", responder.calls[1][2])
        self.assertEqual(responder.calls[2][2]["eligible_evidence"], [])
        self.assertEqual(len(responder.calls[2][2]["critiques"]), 4)
        self.assertNotIn("supporting_record_ids", json.dumps(responder.calls[1][2]["directions"]))
        self.assertEqual({d["id"] for d in responder.calls[1][2]["directions"]}, {"A", "B", "C", "D"})
        self.assertNotIn("evidence_ids", json.dumps(responder.calls[2][2]["critiques"]))  # nothing to cite
        self.assertNotIn("extra_field", out)
        decision = h.notes["decision"]
        self.assertEqual(decision["mode"], "adopt_with_fix")
        self.assertEqual(decision["chosen_labels"], ["A"])
        self.assertEqual(decision["chosen_ids"], [h.notes["presentation"]["A"]])
        self.assertEqual(h.seen, {})

    def test_web_flags_control_which_role_sees_evidence(self) -> None:
        for method, p, c, d in (("pcd_P_o3mini", 1, 0, 0), ("pcd_C_o3mini", 0, 1, 0), ("pcd_D_o3mini", 0, 0, 1),
                                ("pcd_PCD_o3mini", 1, 1, 1)):
            responder = Responder()
            h, _ = run(method, responder)
            payloads = {role: payload for role, _, payload in responder.calls}
            self.assertEqual("earlier_papers" in payloads["proposer"], bool(p), method)
            self.assertEqual("evidence_by_direction" in payloads["critic"], bool(c), method)
            self.assertEqual(bool(payloads["decider"]["eligible_evidence"]), bool(d), method)
            if c:
                self.assertEqual("evidence_ids" in json.dumps(payloads["decider"]["critiques"]), bool(d), method)
            self.assertEqual(h.source, "web")

    def test_decider_may_cite_only_its_own_records(self) -> None:
        _, out = run("pcd_PCD_o3mini", Responder(decision_cites="pas0_0"))
        self.assertEqual(out["supporting_evidence_ids"], ["pas0_0"])
        with self.assertRaises(ValueError):  # cards seen by the proposer are not the decider's evidence
            run("pcd_PCD_o3mini", Responder(decision_cites="card0"))

    def test_ablations_change_only_their_role(self) -> None:
        responder = Responder()
        run("pcd_nocritic_none_o3mini", responder)
        self.assertEqual([c[0] for c in responder.calls], ["proposer", "decider"])
        self.assertNotIn("critiques", responder.calls[1][2])
        responder = Responder()
        h, _ = run("pcd_nodecider_none_o3mini", responder)
        self.assertEqual([c[0] for c in responder.calls], ["proposer", "critic", "writer"])
        self.assertEqual(h.notes["decision"]["chosen_ids"], ["I2"])  # the only "strong" verdict
        chosen = responder.calls[2][2]["analysis_notes"]["chosen_direction"]
        self.assertIn("aluminide", chosen["intervention"])
        self.assertEqual(h.notes["presentation"][chosen["id"]], "I2")
        responder = Responder(k=1)
        run("pcd_k1_none_o3mini", responder)
        self.assertIn("single most promising", LM.proposer_system(1))
        self.assertEqual(len(responder.calls[1][2]["directions"]), 1)
        responder = Responder()
        run("pcd_none_llama", responder)
        self.assertEqual({c[1] for c in responder.calls}, {"llama"})


class LabelStageTests(unittest.TestCase):
    def test_parallel_label_loops_do_not_repeat_work(self) -> None:
        import os
        import random
        import tempfile
        from pathlib import Path

        import pcd_analysis as PA

        runs = [{"method": "pcd_none_o3mini", "run_id": f"r{i}", "status": "ok", "paper_id": "p"} for i in range(6)]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pcd_none_o3mini" / "idea_labels"
            out.mkdir(parents=True)
            (out / "r0.json").write_text("{}")
            labelled: list[str] = []

            def fake_label(run: dict, case: dict) -> None:
                labelled.append(run["run_id"])
                (out / f"{run['run_id']}.json").write_text("{}")
                if run["run_id"] == "r1":  # another process labels r2 meanwhile
                    (out / "r2.json").write_text("{}")

            env = {k: v for k, v in os.environ.items() if k != "MATHG_PENDING_SHUFFLE"}
            with patch.dict(os.environ, env, clear=True), patch.object(PA, "PCD", Path(tmp)), \
                    patch.object(PA.H, "all_runs", return_value=runs), \
                    patch.object(PA.H, "cases", return_value={"p": {}}), patch.object(PA, "label_run", fake_label):
                counts = PA.label_stage(["pcd_none_o3mini"], workers=1)
                self.assertEqual(labelled, ["r1", "r3", "r4", "r5"])
                self.assertEqual(counts, {"jobs": 5, "done": 4, "skipped": 1})
                for name in ("r3.json", "r4.json", "r5.json"):
                    (out / name).unlink()
                labelled.clear()
                os.environ["MATHG_PENDING_SHUFFLE"] = "7"
                PA.label_stage(["pcd_none_o3mini"], workers=1)
            expected = ["r3", "r4", "r5"]
            random.Random(7).shuffle(expected)
            self.assertEqual(labelled, expected)


if __name__ == "__main__":
    unittest.main()
