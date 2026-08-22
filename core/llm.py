"""
LLM provider layer.

Offline-first: every generation works with no network and no API key by using the
deterministic `offline` provider. When the operator supplies an API key, the same
prompt is sent to the live provider over plain HTTPS (no vendor SDKs required, so
the prototype has no heavyweight dependencies and cannot break on SDK drift).

API keys are used for the duration of one request and are never persisted or logged.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

# Provider -> selectable models, mirroring the picker in the UI.
PROVIDERS = {
    "offline": {
        "label": "Offline simulation (no API key)",
        "models": ["approved-local-sim"],
    },
    "anthropic": {
        "label": "Anthropic",
        "models": ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5-20251001"],
    },
    "openai": {
        "label": "OpenAI",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    },
    "google": {
        "label": "Google (Gemini)",
        "models": ["gemini-1.5-pro", "gemini-1.5-flash"],
    },
}

ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
}

TIMEOUT_SECONDS = 90


class LLMResult:
    """Outcome of a generation attempt."""

    def __init__(self, text: str, provider: str, model: str, offline: bool, note: str = ""):
        self.text = text
        self.provider = provider
        self.model = model
        self.offline = offline
        self.note = note  # populated when we fell back to offline


def resolve_api_key(provider: str, supplied_key: str | None) -> str | None:
    """A key typed into the UI wins; otherwise fall back to the environment."""
    if supplied_key:
        return supplied_key.strip()
    env_name = ENV_KEYS.get(provider)
    return os.getenv(env_name) if env_name else None


def is_live_capable(provider: str, supplied_key: str | None = None) -> bool:
    """True when this provider could actually reach a live model right now."""
    return provider in ENV_KEYS and bool(resolve_api_key(provider, supplied_key))


def generate(
    prompt: str,
    fallback_text: str,
    provider: str = "offline",
    model: str = "approved-local-sim",
    api_key: str | None = None,
    max_tokens: int = 4000,
    temperature: float = 0.3,
) -> LLMResult:
    """
    Run one generation.

    `fallback_text` is the deterministic offline draft. It is returned as-is in
    offline mode, and is also what the caller gets back if a live call fails, so
    the demo never dead-ends on a network error.
    """
    if provider == "offline":
        return LLMResult(fallback_text, "offline", "approved-local-sim", offline=True)

    key = resolve_api_key(provider, api_key)
    if not key:
        return LLMResult(
            fallback_text,
            "offline",
            "approved-local-sim",
            offline=True,
            note=f"No API key available for {provider} — generated offline instead.",
        )

    try:
        if provider == "anthropic":
            text = _call_anthropic(prompt, model, key, max_tokens, temperature)
        elif provider == "openai":
            text = _call_openai(prompt, model, key, max_tokens, temperature)
        elif provider == "google":
            text = _call_google(prompt, model, key, max_tokens, temperature)
        else:
            raise ValueError(f"Unknown provider: {provider}")
        return LLMResult(text, provider, model, offline=False)
    except Exception as exc:  # network down, bad key, rate limit, ...
        return LLMResult(
            fallback_text,
            "offline",
            "approved-local-sim",
            offline=True,
            note=f"{provider} call failed ({_short_error(exc)}) — fell back to the offline draft.",
        )


# --------------------------------------------------------------------------
# Provider transports
# --------------------------------------------------------------------------


def _post_json(url: str, payload: dict, headers: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _call_anthropic(prompt, model, key, max_tokens, temperature) -> str:
    body = _post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        },
        {
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
    )
    return "".join(block.get("text", "") for block in body.get("content", []))


def _call_openai(prompt, model, key, max_tokens, temperature) -> str:
    body = _post_json(
        "https://api.openai.com/v1/chat/completions",
        {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        },
        {"content-type": "application/json", "authorization": f"Bearer {key}"},
    )
    return body["choices"][0]["message"]["content"]


def _call_google(prompt, model, key, max_tokens, temperature) -> str:
    body = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        },
        {"content-type": "application/json"},
    )
    parts = body["candidates"][0]["content"]["parts"]
    return "".join(part.get("text", "") for part in parts)


def _short_error(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return "network unreachable"
    return type(exc).__name__
