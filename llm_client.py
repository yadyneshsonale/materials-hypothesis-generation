"""Provider-agnostic LLM client for the MatHG extraction pipeline.

Supports three modes, selected by the MATHG_PROVIDER env var:
  - "openai"  (default if OPENAI_API_KEY is set): any OpenAI-compatible
    chat-completions endpoint. Configure via OPENAI_API_KEY, OPENAI_BASE_URL
    (default https://api.openai.com/v1), OPENAI_MODEL.
  - "trapi": Microsoft-internal TRAPI, authenticated via `az account
    get-access-token`. Configure via TRAPI_ENDPOINT, TRAPI_DEPLOYMENT,
    TRAPI_API_VERSION (defaults match global_sensemaking_eval/graphrag_runner.py).
  - "dryrun" (default if nothing is configured): returns an empty, valid JSON
    payload for every call so the rest of the pipeline (chunking, aggregation,
    I/O) can be exercised without any real API access or cost.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any

import requests

TRAPI_ENDPOINT = os.environ.get("TRAPI_ENDPOINT", "https://trapi.research.microsoft.com/gcr/shared")
TRAPI_DEPLOYMENT = os.environ.get("TRAPI_DEPLOYMENT", "gpt-5.4_2026-03-05")
TRAPI_API_VERSION = os.environ.get("TRAPI_API_VERSION", "2025-04-01-preview")
TRAPI_AUDIENCE = "api://trapi/.default"

_trapi_credential = None  # lazily built; this box's managed identity is authorized, no az login needed


class LLMError(RuntimeError):
    pass


class TruncatedError(LLMError):
    """Raised when the model's response was cut off by max_tokens (finish_reason == 'length').

    Distinguished from other LLMError causes so callers can react by shrinking the input
    and retrying, instead of just retrying the identical request (which fails identically).
    """


def _provider() -> str:
    explicit = os.environ.get("MATHG_PROVIDER")
    if explicit:
        return explicit
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return "dryrun"


def _trapi_token() -> str:
    global _trapi_credential
    if _trapi_credential is None:
        from azure.identity import AzureCliCredential, ChainedTokenCredential, ManagedIdentityCredential
        _trapi_credential = ChainedTokenCredential(AzureCliCredential(), ManagedIdentityCredential())
    try:
        return _trapi_credential.get_token(TRAPI_AUDIENCE).token
    except Exception as e:  # noqa: BLE001
        raise LLMError(f"TRAPI token fetch failed: {e}") from e


def chat_json(system: str, user: str, max_tokens: int = 4000, retries: int = 3) -> Any:
    """Call the configured LLM and parse the reply as JSON. Returns [] / {} on dryrun."""
    provider = _provider()

    if provider == "dryrun":
        return {}

    if provider == "openai":
        api_key = os.environ["OPENAI_API_KEY"]
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
    elif provider == "trapi":
        token = _trapi_token()
        url = f"{TRAPI_ENDPOINT}/openai/deployments/{TRAPI_DEPLOYMENT}/chat/completions?api-version={TRAPI_API_VERSION}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_completion_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
    else:
        raise LLMError(f"unknown MATHG_PROVIDER={provider!r}")

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            choice = resp.json()["choices"][0]
            content = choice["message"]["content"]
            if choice.get("finish_reason") == "length":
                raise TruncatedError(f"response truncated at max_tokens={max_tokens}")
            return json.loads(content)
        except TruncatedError:
            raise  # not transient - let the caller shrink the input instead of blindly retrying
        except Exception as e:  # noqa: BLE001 - want to retry on any other transient failure
            last_err = e
            time.sleep(2 ** attempt)
    raise LLMError(f"LLM call failed after {retries} attempts: {last_err}")


def provider_info() -> str:
    return _provider()


_encoder = None


def estimate_tokens(text: str) -> int:
    """Real tokenizer count via tiktoken (cl100k_base is a close-enough proxy across
    modern chat models for budgeting purposes); falls back to a ~4-chars/token estimate
    if tiktoken isn't installed."""
    global _encoder
    if _encoder is None:
        try:
            import tiktoken
            _encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:  # noqa: BLE001
            _encoder = False
    if _encoder is False:
        return len(text) // 4
    return len(_encoder.encode(text))


def context_window_tokens() -> int:
    return int(os.environ.get("MATHG_CONTEXT_WINDOW", "128000"))


def resilient_chat_json(system: str, user: str, max_tokens: int = 2000, max_retries: int = 6) -> Any | None:
    """chat_json with a longer outer backoff (up to ~60s between attempts), for the
    agent's higher-level calls (compose/critique/refine/merge/judge) where a single
    TRAPI 429 shouldn't silently degrade a whole hypothesis into a null-scored record.
    Returns None (never raises) after exhausting retries, so callers can skip cleanly."""
    for attempt in range(max_retries):
        try:
            return chat_json(system, user, max_tokens=max_tokens)
        except LLMError as e:
            wait = min(2 ** attempt, 60)
            print(f"[llm] WARN: call failed (attempt {attempt + 1}/{max_retries}): {e} - retrying in {wait}s")
            time.sleep(wait)
    print(f"[llm] ERROR: call failed after {max_retries} attempts, giving up")
    return None
