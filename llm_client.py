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
import re
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

    if provider == "trapi":
        temperature = os.environ.get("MATHG_TEMPERATURE")
        return trapi_chat_json(TRAPI_DEPLOYMENT, system, user, max_tokens=max_tokens,
                               temperature=float(temperature) if temperature else None, retries=max(retries, 8))

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
        chat_template_kwargs = os.environ.get("OPENAI_CHAT_TEMPLATE_KWARGS")
        if chat_template_kwargs:
            try:
                parsed_kwargs = json.loads(chat_template_kwargs)
            except json.JSONDecodeError as error:
                raise LLMError(f"OPENAI_CHAT_TEMPLATE_KWARGS is not valid JSON: {error}") from error
            if not isinstance(parsed_kwargs, dict):
                raise LLMError("OPENAI_CHAT_TEMPLATE_KWARGS must be a JSON object")
            payload["chat_template_kwargs"] = parsed_kwargs
    elif provider == "trapi":
        token = _trapi_token()
        url = f"{TRAPI_ENDPOINT}/openai/deployments/{TRAPI_DEPLOYMENT}/chat/completions?api-version={TRAPI_API_VERSION}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_completion_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        if os.environ.get("MATHG_TEMPERATURE"):
            payload["temperature"] = float(os.environ["MATHG_TEMPERATURE"])
    else:
        raise LLMError(f"unknown MATHG_PROVIDER={provider!r}")

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            timeout = float(os.environ.get("MATHG_REQUEST_TIMEOUT", "120"))
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
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


JUDGE_TRAPI_DEPLOYMENT = os.environ.get("JUDGE_TRAPI_DEPLOYMENT", "gpt-5.6-sol_2026-07-09")


def judge_info() -> str:
    """Identifies the judge backend in evaluation outputs."""
    if os.environ.get("JUDGE_PROVIDER", "trapi") == "trapi":
        return f"trapi:{JUDGE_TRAPI_DEPLOYMENT}"
    return f"{os.environ.get('JUDGE_PROVIDER')}:{os.environ.get('OPENAI_MODEL', '')}"


def endpoint_for(deployment: str) -> str:
    """The TRAPI instance for a deployment. JUDGE_TRAPI_ENDPOINT, if set, serves the judge deployment only (experiment
    36 used a second instance of the same GPT-5.6 deployment when the shared one rate-limited nearly every call)."""
    judge_endpoint = os.environ.get("JUDGE_TRAPI_ENDPOINT")
    if judge_endpoint and deployment == JUDGE_TRAPI_DEPLOYMENT:
        return judge_endpoint.rstrip("/")
    return TRAPI_ENDPOINT


def trapi_chat_json(deployment: str, system: str, user: str, *, max_tokens: int,
                    token_field: str = "max_completion_tokens", temperature: float | None = None,
                    retries: int = 6, reasoning_effort: str | None = None) -> Any:
    """JSON chat call to a named TRAPI deployment.

    token_field follows the deployment's API: OpenAI reasoning and recent models take max_completion_tokens,
    while some open models take max_tokens. temperature is omitted when None (required for o-series models).
    reasoning_effort ("low", "medium", "high") is sent only when given (o-series models only).
    Rate limits (HTTP 429) are retried after the wait TRAPI reports; other transient failures are retried
    with exponential backoff. Truncated responses raise TruncatedError.
    """
    url = (f"{endpoint_for(deployment)}/openai/deployments/{deployment}"
           f"/chat/completions?api-version={TRAPI_API_VERSION}")
    payload: dict[str, Any] = {
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        token_field: max_tokens,
        "response_format": {"type": "json_object"},
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if reasoning_effort is not None:
        payload["reasoning_effort"] = reasoning_effort
    retries = max(retries, int(os.environ.get("MATHG_MIN_RETRIES", "0")))  # resilience under shared rate limits
    timeout = float(os.environ.get("MATHG_REQUEST_TIMEOUT", "240"))
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            headers = {"Authorization": f"Bearer {_trapi_token()}", "Content-Type": "application/json"}
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if resp.status_code == 429:
                match = re.search(r"in (\d+) seconds", resp.text)
                time.sleep(min(int(match.group(1)) + 2 if match else 30, 120))
                last_err = LLMError(f"rate limited: {resp.text[:160]}")
                continue
            resp.raise_for_status()
            choice = resp.json()["choices"][0]
            if choice.get("finish_reason") == "length":
                raise TruncatedError(f"TRAPI response from {deployment} truncated at {token_field}={max_tokens}")
            return json.loads(choice["message"]["content"])
        except TruncatedError:
            raise
        except Exception as e:  # noqa: BLE001 - retry transient failures
            last_err = e
            time.sleep(2 ** min(attempt, 5))
    raise LLMError(f"TRAPI call to {deployment} failed after {retries} attempts: {last_err}")


SINGLE_TOOL_DEPLOYMENTS = ("Llama-",)
SINGLE_TOOL_NAME = "act"


def wrap_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Some deployments (Llama on Azure) accept only one tool definition, so every tool becomes one 'act' call."""
    lines = []
    for tool in tools:
        fn = tool["function"]
        lines.append(f"- {fn['name']}: {fn.get('description', '')} Arguments schema: "
                     f"{json.dumps(fn.get('parameters', {}).get('properties', {}))}")
    return [{"type": "function", "function": {
        "name": SINGLE_TOOL_NAME,
        "description": "Call one of the available tools. Available tools:\n" + "\n".join(lines),
        "parameters": {"type": "object", "properties": {
            "tool": {"type": "string", "enum": [t["function"]["name"] for t in tools]},
            "arguments": {"type": "object", "description": "Arguments for the chosen tool, matching its schema."}},
            "required": ["tool", "arguments"]}}}]


def _wrap_message(message: dict[str, Any]) -> dict[str, Any]:
    if not message.get("tool_calls"):
        return message
    calls = []
    for call in message["tool_calls"]:
        try:
            arguments = json.loads(call["function"].get("arguments") or "{}")
        except json.JSONDecodeError:
            arguments = {}
        calls.append({**call, "function": {"name": SINGLE_TOOL_NAME, "arguments": json.dumps(
            {"tool": call["function"]["name"], "arguments": arguments})}})
    return {**message, "tool_calls": calls}


def _unwrap_message(message: dict[str, Any]) -> dict[str, Any]:
    if not message.get("tool_calls"):
        return message
    calls = []
    for call in message["tool_calls"]:
        try:
            wrapped = json.loads(call["function"].get("arguments") or "{}")
        except json.JSONDecodeError:
            wrapped = {}
        name = str(wrapped.get("tool", "")) if isinstance(wrapped, dict) else ""
        arguments = wrapped.get("arguments", {}) if isinstance(wrapped, dict) else {}
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}
        calls.append({"id": call.get("id", ""), "type": "function",
                      "function": {"name": name or "unknown", "arguments": json.dumps(arguments)}})
    return {**message, "tool_calls": calls}


def trapi_chat_with_tools(messages: list[dict[str, Any]], tools: list[dict[str, Any]], retries: int = 6) -> dict[str, Any]:
    """Tool-calling chat turn on the TRAPI generator deployment (TRAPI_DEPLOYMENT). Returns the assistant message."""
    url = (f"{TRAPI_ENDPOINT}/openai/deployments/{TRAPI_DEPLOYMENT}"
           f"/chat/completions?api-version={TRAPI_API_VERSION}")
    single = TRAPI_DEPLOYMENT.startswith(SINGLE_TOOL_DEPLOYMENTS)
    if single:
        tools = wrap_tools(tools)
        messages = [_wrap_message(m) if m.get("role") == "assistant" else m for m in messages]
    payload: dict[str, Any] = {"messages": messages, "tools": tools, "tool_choice": "auto",
                               "max_completion_tokens": 5000}
    if os.environ.get("MATHG_TEMPERATURE"):
        payload["temperature"] = float(os.environ["MATHG_TEMPERATURE"])
    timeout = float(os.environ.get("MATHG_REQUEST_TIMEOUT", "240"))
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            headers = {"Authorization": f"Bearer {_trapi_token()}", "Content-Type": "application/json"}
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if resp.status_code == 429:
                match = re.search(r"in (\d+) seconds", resp.text)
                time.sleep(min(int(match.group(1)) + 2 if match else 30, 120))
                last_err = LLMError(f"rate limited: {resp.text[:160]}")
                continue
            resp.raise_for_status()
            message = resp.json()["choices"][0]["message"]
            message = {k: v for k, v in message.items() if k in ("role", "content", "tool_calls")}
            return _unwrap_message(message) if single else message
        except Exception as e:  # noqa: BLE001 - retry transient failures
            last_err = e
            time.sleep(2 ** min(attempt, 5))
    raise LLMError(f"TRAPI tool call to {TRAPI_DEPLOYMENT} failed after {retries} attempts: {last_err}")


def judge_chat_json(system: str, user: str, max_tokens: int = 8000, retries: int = 6) -> Any:
    """Judge calls go to TRAPI GPT-5.6 by default, so the local generator never scores its own output."""
    if os.environ.get("JUDGE_PROVIDER", "trapi") != "trapi":
        return chat_json(system, user, max_tokens=max_tokens, retries=retries)
    return trapi_chat_json(JUDGE_TRAPI_DEPLOYMENT, system, user, max_tokens=max_tokens, retries=retries)


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
