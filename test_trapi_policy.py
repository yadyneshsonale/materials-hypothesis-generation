"""Tests for the TRAPI retry policy (experiment 42, loop.md 23.1 incident notes): honour Retry-After with a
process-wide gate, never retry non-transient errors, fail fast once blocked."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from requests.structures import CaseInsensitiveDict

import llm_client as lc


class Resp:
    def __init__(self, status: int, text: str = "", content: str = '{"ok": true}',
                 headers: dict | None = None) -> None:
        self.status_code, self.text, self._content = status, text, content
        self.headers = CaseInsensitiveDict(headers or {})

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._content}, "finish_reason": "stop"}]}


class PolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        lc._TRAPI_BLOCKED.clear()
        for state in (lc._GATES, lc._PACE, lc._NEXT):
            state.clear()
        self.sleeps: list[float] = []
        self.now = 1000.0
        self.post_times: list[float] = []

    def tearDown(self) -> None:
        lc._TRAPI_BLOCKED.clear()
        for state in (lc._GATES, lc._PACE, lc._NEXT):
            state.clear()

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def call(self, responses: list[Resp], env: dict | None = None) -> tuple[object, int]:
        calls = []

        def post(url, headers, json, timeout):
            calls.append(headers)
            self.post_times.append(self.now)
            return responses.pop(0)

        with patch.object(lc.requests, "post", side_effect=post), patch.object(lc.time, "sleep", self.sleep), \
                patch.object(lc.time, "monotonic", lambda: self.now), \
                patch.object(lc, "_trapi_token", return_value="t"), patch.dict(os.environ, env or {}):
            try:
                out = lc.trapi_chat_json("dep", "s", "u", max_tokens=10)
            except Exception as error:  # noqa: BLE001
                out = error
        self.headers = calls
        return out, len(calls)

    def test_403_stops_at_once_and_blocks_later_calls(self) -> None:
        out, n = self.call([Resp(403, '{"error":"PrincipalBlocked","reason":"retry-flood"}'), Resp(200)])
        self.assertIsInstance(out, lc.TrapiBlocked)
        self.assertIn("retry-flood", str(out))
        self.assertEqual(n, 1)
        out, n = self.call([Resp(200)])
        self.assertIsInstance(out, lc.TrapiBlocked)
        self.assertEqual(n, 0)

    def test_429_waits_for_the_body_hint_then_succeeds(self) -> None:
        out, n = self.call([Resp(429, "retry after 5 seconds"), Resp(429, "retry after 5 seconds"), Resp(200)])
        self.assertEqual(out, {"ok": True})
        self.assertEqual(n, 3)
        self.assertGreaterEqual(self.post_times[1] - self.post_times[0], 5)
        self.assertGreaterEqual(self.post_times[2] - self.post_times[1], 5)

    def test_429_without_a_hint_backs_off_exponentially(self) -> None:
        out, n = self.call([Resp(429, "busy"), Resp(429, "busy"), Resp(200)])
        self.assertEqual(out, {"ok": True})
        self.assertGreaterEqual(self.post_times[1] - self.post_times[0], 10)  # 10 * 2**0
        self.assertGreaterEqual(self.post_times[2] - self.post_times[1], 20)  # 10 * 2**1

    def test_rate_limits_pace_later_requests(self) -> None:
        self.call([Resp(429, "busy", headers={"retry-after": "3"}), Resp(429, "busy", headers={"retry-after": "3"}),
                   Resp(200)])
        url = next(iter(lc._PACE))
        pace = lc.PACE_UP * lc.PACE_DOWN  # 1 s after the first event, grown once more, then one success
        self.assertAlmostEqual(lc._PACE[url], pace)
        self.post_times.clear()
        self.call([Resp(200)])
        self.call([Resp(200)])
        self.assertGreaterEqual(self.post_times[1] - self.post_times[0], pace - 1e-9)

    def test_pace_is_capped(self) -> None:
        for _ in range(40):
            self.now += 100  # each 429 arrives after the previous gate has opened: a new event
            with patch.object(lc.time, "monotonic", lambda: self.now):
                lc._rate_limited("u", 30)
        self.assertEqual(lc._PACE["u"], lc.MAX_PACE)

    def test_in_flight_rate_limits_double_the_pace_once(self) -> None:
        with patch.object(lc.time, "monotonic", lambda: self.now):
            for _ in range(5):  # five requests in flight when the budget ran out
                lc._rate_limited("u", 30)
        self.assertEqual(lc._PACE["u"], 1.0)

    def test_successes_shrink_the_pace_to_zero(self) -> None:
        url = (f"{lc.endpoint_for('dep')}/openai/deployments/dep/chat/completions?api-version={lc.TRAPI_API_VERSION}")
        lc._PACE[url] = 0.55  # 0.495 after one success: below 0.5, so pacing stops
        self.call([Resp(200)])
        self.assertEqual(lc._PACE[url], 0.0)

    def test_429_honours_retry_after_header(self) -> None:
        out, n = self.call([Resp(429, "busy", headers={"retry-after": "600"}), Resp(200)])
        self.assertEqual(out, {"ok": True})
        self.assertEqual(n, 2)
        self.assertGreaterEqual(self.post_times[1] - self.post_times[0], 600)

    def test_429_honours_retry_after_ms_header(self) -> None:
        out, _ = self.call([Resp(429, "busy", headers={"retry-after-ms": "300000"}), Resp(200)])
        self.assertEqual(out, {"ok": True})
        self.assertGreaterEqual(self.post_times[1] - self.post_times[0], 300)

    def test_gate_holds_back_every_call_to_the_url(self) -> None:
        url = (f"{lc.endpoint_for('dep')}/openai/deployments/dep/chat/completions?api-version={lc.TRAPI_API_VERSION}")
        lc._close_gate(url, 120)  # as if another thread had just been rate limited
        out, n = self.call([Resp(200)])
        self.assertEqual(out, {"ok": True})
        self.assertGreaterEqual(self.post_times[0] - 1000.0, 120)

    def test_non_transient_errors_are_not_retried(self) -> None:
        for status in (400, 404):
            out, n = self.call([Resp(status, "bad request"), Resp(200)])
            self.assertIsInstance(out, lc.TrapiRejected)
            self.assertEqual(n, 1)

    def test_server_errors_are_retried(self) -> None:
        out, n = self.call([Resp(500, "oops"), Resp(200)])
        self.assertEqual(out, {"ok": True})
        self.assertEqual(n, 2)

    def test_attempts_are_capped_whatever_min_retries_says(self) -> None:
        out, n = self.call([Resp(429, "retry after 1 seconds") for _ in range(30)], {"MATHG_MIN_RETRIES": "20"})
        self.assertIsInstance(out, lc.LLMError)
        self.assertEqual(n, lc.MAX_TRAPI_ATTEMPTS)

    def test_response_log(self) -> None:
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "trapi.jsonl")
            out, _ = self.call([Resp(429, "busy", headers={"retry-after": "7"}), Resp(200)], {"MATHG_TRAPI_LOG": log})
            self.assertEqual(out, {"ok": True})
            lines = [json.loads(x) for x in open(log, encoding="utf-8")]
        self.assertEqual([x["status"] for x in lines], [429, 200])
        self.assertEqual(lines[0]["retry-after"], "7")
        self.assertIn("body", lines[0])
        self.assertNotIn("body", lines[1])

    def test_workload_id_header(self) -> None:
        self.call([Resp(200)])
        self.assertEqual(self.headers[0]["X-TRAPI-Workload-ID"], lc.WORKLOAD_ID)


if __name__ == "__main__":
    unittest.main()
