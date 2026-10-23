from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import llm_client
import rubric_eval as rx
from temporal_hypothesis_benchmark import RetrievalRecord


PAPER = (
    "Effect of Cr on HfMoTaTiZr\n\nAbstract\nAdding 4.2 at.% Cr to HfMoTaTiZr formed a reticulated Laves phase "
    "and raised the yield strength by 13.5% at room temperature.\nResults\nThe lattice parameter contracted from "
    "3.392 Å to 3.325 Å after Cr addition, indicating solid solution hardening.\n"
)


class TextHandlingTests(unittest.TestCase):
    def test_strip_back_matter_only_after_body(self) -> None:
        body = "Intro\n" + "x" * 1000 + "\nResults\n" + "y" * 1000
        text = body + "\nReferences\n[1] Someone 2020.\n"
        self.assertEqual(rx.strip_back_matter(text), body)
        early = "Funding\nNot really back matter\n" + "z" * 2000
        self.assertEqual(rx.strip_back_matter(early), early)

    def test_windows_respect_size_and_keep_content(self) -> None:
        text = "\n".join(f"paragraph {i} " + "w" * 90 for i in range(60))
        parts = rx.windows(text, size=1000)
        self.assertTrue(all(len(p) <= 1000 for p in parts))
        self.assertEqual(rx.normalise(" ".join(parts)), rx.normalise(text))
        self.assertEqual(rx.windows("short", size=1000), ["short"])

    def test_quote_validation_tolerates_formatting_but_rejects_inventions(self) -> None:
        norm = rx.normalise(PAPER)
        quotes = ["Adding 4.2 at.% Cr to   HfMoTaTiZr formed a reticulated Laves phase",
                  "Cr addition made the alloy ductile at 1200 C",
                  "too short"]
        self.assertEqual(rx.valid_quotes(quotes, norm), [quotes[0]])
        self.assertEqual(rx.valid_quotes("not a list", norm), [])

    def test_render_skips_not_stated_and_includes_quote(self) -> None:
        item = {"base_system": "HfMoTaTiZr", "intervention": "add 4.2 at.% Cr", "processing": "not stated",
                "property_change": "yield +13.5%", "quotes": ["Adding 4.2 at.% Cr"]}
        text = rx.render("effects", item)
        self.assertIn("Intervention effect.", text)
        self.assertIn("Intervention: add 4.2 at.% Cr.", text)
        self.assertNotIn("Processing", text)
        self.assertIn('Quote: "Adding 4.2 at.% Cr"', text)
        self.assertTrue(rx.is_substantive("effects", item))
        self.assertFalse(rx.is_substantive("effects", {"intervention": "not stated"}))


class ExtractionTests(unittest.TestCase):
    def test_items_without_a_verbatim_quote_are_dropped(self) -> None:
        reply = {"items": [
            {"intervention": "add Cr", "quotes": ["raised the yield strength by 13.5% at room temperature"]},
            {"intervention": "add Al", "quotes": ["Al addition doubled ductility in this work"]},
            {"intervention": "not stated", "quotes": ["indicating solid solution hardening"]},
            "junk",
        ]}
        with patch.object(rx.lc, "chat_json", return_value=reply):
            kept, stats = rx.extract_window("effects", "P1", "t", PAPER, "1/1")
        self.assertEqual([k["intervention"] for k in kept], ["add Cr"])
        self.assertEqual(stats["proposed"], 4)
        self.assertEqual(stats["no_valid_quote"], 1)
        self.assertEqual(stats["empty"], 1)
        self.assertEqual(stats["malformed"], 1)

    def test_truncated_windows_are_split_and_retried(self) -> None:
        long_window = "\n".join([PAPER] * 200)
        calls = []

        def fake(system, user, max_tokens=4000, retries=3):
            calls.append(len(json.loads(user)["text"]))
            if len(calls) == 1:
                raise llm_client.TruncatedError("too long")
            return {"items": [{"intervention": "add Cr", "quotes": ["formed a reticulated Laves phase"]}]}

        with patch.object(rx.lc, "chat_json", side_effect=fake):
            kept, stats = rx.extract_window("effects", "P1", "t", long_window, "1/1")
        self.assertEqual(len(calls), 3)
        self.assertLess(max(calls[1:]), calls[0])
        self.assertEqual(len(kept), 2)
        self.assertEqual({k["part"] for k in kept}, {"1/1a", "1/1b"})


def _record(rid: str, pid: str, date: str, text: str) -> RetrievalRecord:
    return RetrievalRecord(rid, pid, date, "rubric:effects", text, {})


class PackingAndLeakageTests(unittest.TestCase):
    def test_pack_respects_budget_and_record_cap(self) -> None:
        pool = [_record(f"P{i}::r", f"P{i}", "2020-01-01", "chromium laves " + "x" * 1500) for i in range(40)]
        packed = rx.pack("chromium laves", pool)
        used = sum(min(len(r.text), rx.RECORD_MAX_CHARS) for r in packed)
        self.assertLessEqual(used, rx.EVIDENCE_BUDGET_CHARS)
        self.assertLessEqual(len(packed), rx.MAX_RECORDS)
        self.assertGreater(len(packed), 5)

    def test_cards_get_a_larger_cap_within_the_same_budget(self) -> None:
        self.assertEqual(rx.record_cap("card"), 3200)
        self.assertEqual(rx.record_cap("effects"), rx.RECORD_MAX_CHARS)
        cards = [_record(f"P{i}::c", f"P{i}", "2020-01-01", "chromium laves " + "y" * 2900) for i in range(20)]
        packed = rx.pack("chromium laves", cards, rx.record_cap("card"))
        self.assertLessEqual(sum(min(len(r.text), 3200) for r in packed), rx.EVIDENCE_BUDGET_CHARS)
        self.assertEqual(len(packed), 5)

    def test_case_pool_keeps_only_eligible_papers(self) -> None:
        case = {"paper_id": "T", "publication_date": "2024-01-02"}
        records = [_record("A::r", "A", "2020-01-01", "a"), _record("T::r", "T", "2024-01-02", "t"),
                   _record("L::r", "L", "2025-01-01", "late")]
        rx._cache.pop("pool_T_effects", None)
        with patch.object(rx, "build_corpus", return_value=({"A"}, [], [])), \
                patch.object(rx, "rubric_records", return_value=records), \
                patch.object(rx, "metadata", return_value={}), \
                patch.dict(rx._cache, {"v2": []}):
            eligible, pool = rx.case_pool(case, "effects")
        self.assertEqual([r.record_id for r in pool], ["A::r"])
        rx._cache.pop("pool_T_effects", None)

    def test_leakage_audit_counts_each_violation(self) -> None:
        meta = {"T": {"work_family_id": "fam"}, "F": {"work_family_id": "fam"}, "A": {"work_family_id": "a"}}
        records = [_record("A::r", "A", "2020-01-01", ""), _record("T::r", "T", "2023-01-01", ""),
                   _record("F::r", "F", "2023-01-01", ""), _record("L::r", "A", "2024-06-01", "")]
        with patch.object(rx, "metadata", return_value=meta):
            counts = rx.leakage_audit(records, {"paper_id": "T", "publication_date": "2024-01-02"})
        self.assertEqual(counts, {"temporal_violations": 1, "test_paper_leaks": 1, "family_leaks": 2})

    def test_audit_payload_is_target_free(self) -> None:
        run = {"run_id": "PMCX__broad__effects__s1", "status": "ok", "paper_id": "PMCX", "query": "q",
               "generation": {"hypothesis": "h"}, "cited_evidence": [{"record_id": "A::r", "text": "t"}]}
        sent = {}

        def capture(system, user, max_tokens=8000, retries=6):
            sent["payload"] = json.loads(user)
            return {"claims": []}

        with patch.object(rx, "load_runs", return_value={run["run_id"]: run}), \
                patch.object(rx.lc, "judge_chat_json", side_effect=capture), \
                patch.object(rx, "atomic_json"):
            result = rx.audit_stage(workers=1, resume=False)
        self.assertEqual(result["done"], 1)
        self.assertEqual(set(sent["payload"]), {"query", "hypothesis", "cited_evidence"})


if __name__ == "__main__":
    unittest.main()
