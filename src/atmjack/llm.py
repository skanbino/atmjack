"""Minimal OpenAI-compatible chat client (stdlib only)."""

from __future__ import annotations

import json
import os
import urllib.request

DEFAULT_MODEL = os.environ.get("ATMJACK_MODEL", "gpt-4o-mini")
_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
API_URL = f"{_BASE_URL}/chat/completions"


def ask(
 prompt: str,
 *,
 model: str | None = None,
 system: str | None = None,
 timeout: int = 60,
) -> str:
 """Send a single-turn chat request and return the assistant text."""
 api_key = os.environ.get("OPENAI_API_KEY")
 if not api_key:
 raise RuntimeError("OPENAI_API_KEY not set")

 messages: list[dict[str, str]] = []
 if system:
 messages.append({"role": "system", "content": system})
 messages.append({"role": "user", "content": prompt})

 body = json.dumps({"model": model or DEFAULT_MODEL, "messages": messages}).encode("utf-8")
 req = urllib.request.Request(
 API_URL,
 data=body,
 headers={
 "Content-Type": "application/json",
 "Authorization": f"Bearer {api_key}",
 },
 method="POST",
 )
 with urllib.request.urlopen(req, timeout=timeout) as resp:
 payload = json.loads(resp.read())
 return str(payload["choices"][0]["message"]["content"])