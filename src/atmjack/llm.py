"""thin LLM wrapper -- pluggable backend, no framework."""
from __future__ import annotations

import json
import os
import urllib.request

def chat(prompt: str, model: str = "gpt-4o-mini") -> str:
 api_key = os.environ.get("OPENAI_API_KEY")
 if not api_key:
 raise RuntimeError("OPENAI_API_KEY not set")
 body = json.dumps({
 "model": model,
 "messages": [{"role": "user", "content": prompt}],
 }).encode()
 req = urllib.request.Request(
 "https://api.openai.com/v1/chat/completions",
 data=body,
 headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
 )
 with urllib.request.urlopen(req, timeout=60) as resp:
 payload = json.loads(resp.read())
 return payload["choices"][0]["message"]["content"]
