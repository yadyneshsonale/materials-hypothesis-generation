"""Tests for the synthesis methods (experiment 38, loop.md 19.1)."""

from __future__ import annotations

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


def pool(kind: str) -> list[RetrievalRecord]:
    words = ("silicide", "aluminide", "chromia", "zirconia")
    return [RetrievalRecord(f"pas{i}_{j}", f"P{i}", "2020-01-01", "web:Results", f"{w} coating oxide scale " * 80,
                            {"source": "web"}) for i, w in enumerate(words) for j in range(6)]


class Responder:
    """Fake model: every draft names its draft number; the synthesis cites what it is told to."""

    def __init__(self, fail_models: tuple[str, ...] = (), cite: str | None = None):
        self.calls: list[tuple[str, str, dict]] = []
        self.fail_models = fail_models
        self.cite = cite

    def __call__(self, role, model, system, payload, max_out=None):
        self.calls.append((role, model, payload))
        if model in self.fail_models:
            raise RuntimeError("model unavailable")
        n = role.split("_")[-1]
        cites = [self.cite] if self.cite and payload.get("eligible_evidence") else []  # cites only given records
        return {"hypothesis": f"Draft {n}: a silicide coating protects cast HfNbTaTiZr.",
                "intervention": f"silicide coating {n}", "conditions": "air, 1000 C", "mechanism": "oxide scale",
                "predicted_outcome": "lower mass gain", "supporting_evidence_ids": cites, "conflicting_evidence_ids": []}


def run(method: str, responder: Responder) -> tuple[H.Harness, dict]:
    h = H.Harness(CASE, "problem_constrained", 1)
    with patch.object(h, "ask", side_effect=responder), \
            patch.object(h, "pool", side_effect=lambda representation: pool(representation)):
        out = H.METHODS[method](h)
    return h, out


class SynthTests(unittest.TestCase):
    def test_registered(self) -> None:
        for method in LM.SYNTH_CONFIGS:
            self.assertIn(method, H.METHODS)
        self.assertEqual(LM.CROWD, ("o3mini", "o1", "4o", "4omini", "llama"))

    def test_k4_drafts_then_synthesis_with_neutral_shuffled_labels(self) -> None:
        responder = Responder()
        h, out = run("synth_k4_b_o3mini", responder)
        roles = [c[0] for c in responder.calls]
        self.assertEqual(roles, ["draft_1", "draft_2", "draft_3", "draft_4", "writer"])
        self.assertEqual({c[1] for c in responder.calls}, {"o3mini"})
        shown = responder.calls[-1][2]["drafts"]
        self.assertEqual([d["label"] for d in shown], ["A", "B", "C", "D"])
        self.assertTrue(all("model" not in d and "id" not in d for d in shown))  # no model names, no draft IDs
        mapping = h.notes["presentation"]
        self.assertEqual(sorted(mapping.values()), ["D1", "D2", "D3", "D4"])
        for item in shown:  # every label maps back to the draft it shows
            draft = next(d for d in h.notes["drafts"] if d["id"] == mapping[item["label"]])
            self.assertEqual(item["intervention"], draft["intervention"])
        self.assertEqual(responder.calls[-1][2]["eligible_evidence"], [])
        self.assertNotIn("extra", out)

    def test_presentation_is_seeded(self) -> None:
        first = run("synth_k4_b_o3mini", Responder())[0].notes["presentation"]
        second = run("synth_k4_b_o3mini", Responder())[0].notes["presentation"]
        self.assertEqual(first, second)

    def test_crowd_uses_every_model_and_survives_a_failed_draft(self) -> None:
        responder = Responder(fail_models=("o1",))
        h, _ = run("synth_crowd_b_o3mini", responder)
        drafted = [c[1] for c in responder.calls if c[0].startswith("draft_")]
        self.assertEqual(drafted[:2], ["o3mini", "o1"])
        self.assertIn("llama", drafted)
        self.assertEqual(len(h.notes["drafts"]), 4)
        self.assertEqual(h.notes["draft_failures"][0]["model"], "o1")
        self.assertEqual(len(responder.calls[-1][2]["drafts"]), 4)
        self.assertEqual(responder.calls[-1][1], "o3mini")

    def test_every_draft_failing_raises(self) -> None:
        with self.assertRaises(ValueError):
            run("synth_k1_b_o3mini", Responder(fail_models=("o3mini",)))

    def test_mixed_gives_evidence_only_to_web_drafts_and_the_synthesis(self) -> None:
        responder = Responder(cite="pas0_0")
        h, out = run("synth_mixed_b_o3mini", responder)
        payloads = {c[0]: c[2] for c in responder.calls}
        self.assertEqual(payloads["draft_1"]["eligible_evidence"], [])
        self.assertEqual(payloads["draft_2"]["eligible_evidence"], [])
        self.assertTrue(payloads["draft_3"]["eligible_evidence"])
        self.assertTrue(payloads["draft_4"]["eligible_evidence"])
        self.assertTrue(payloads["writer"]["eligible_evidence"])
        self.assertEqual(h.source, "web")
        self.assertLessEqual(h.notes["evidence"]["chars"], LM.SYNTH_WEB_BUDGET)
        self.assertEqual(out["supporting_evidence_ids"], ["pas0_0"])
        web_drafts = [d for d in h.notes["drafts"] if d["web"]]
        self.assertEqual([d["supporting_evidence_ids"] for d in web_drafts], [["pas0_0"], ["pas0_0"]])
        closed = [d for d in payloads["writer"]["drafts"] if not d["supporting_evidence_ids"]]
        self.assertEqual(len(closed), 2)

    def test_closed_book_synthesis_validates_against_no_records(self) -> None:
        with patch.object(H, "_validate_generation", wraps=H._validate_generation) as validate:
            _, out = run("synth_k1_b_o3mini", Responder(cite="pas0_0"))
        self.assertEqual(len(validate.call_args_list), 2)  # one draft, one synthesis
        self.assertTrue(all(args.args[1] == set() for args in validate.call_args_list))
        self.assertEqual(out["supporting_evidence_ids"], [])

if __name__ == "__main__":
    unittest.main()
