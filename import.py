"""One-shot repair for the atmjack repo.

Rewrites the seven modules with broken indentation, patches utils.py,
adds an import-regression test, then runs the full check suite.
Run from the repo root: uv run python fix_everything.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src" / "atmjack"

if not (SRC / "utils.py").exists():
    sys.exit("Run this from the repo root (src/atmjack/utils.py not found).")

ACCESS = '''"""Active Directory access helpers built on windapsearch."""

import shutil
import subprocess

def windapsearch(dc: str, domain: str, user: str, password: str) -> dict:
 """Run windapsearch against a domain controller and return raw output."""
 bin_path = shutil.which("windapsearch") or shutil.which("windapsearch.py")
 if not bin_path:
     raise RuntimeError("windapsearch not on PATH -- add _ref/windapsearch to PATH")
     cmd = [bin_path, "--dc-ip", dc, "-d", domain, "-u", user, "-p", password]
     proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
     return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
'''

CREDS = '''"""Credential testing helpers built on hydra."""

import shutil
import subprocess

def hydra(host: str, service: str, userlist: str, passlist: str) -> dict:
 """Run hydra against a service and collect discovered credentials."""
 if not shutil.which("hydra"):
     raise RuntimeError("hydra not on PATH")
     cmd = ["hydra", "-L", userlist, "-P", passlist, "-I", "-f", f"{service}://{host}"]
     proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, check=False)
     found = []
     for line in proc.stdout.splitlines():
         if "password:" in line.lower():
             found.append(line.strip())
             return {"found": found, "raw": proc.stdout}
'''

LLM = '''"""Minimal OpenAI chat-completion client using only the standard library."""

import json
import os
import urllib.request

def chat(prompt: str, model: str = "gpt-4o-mini") -> str:
 """Send a single-user-turn chat completion and return the reply text."""
 api_key = os.environ.get("OPENAI_API_KEY")
 if not api_key:
     raise RuntimeError("OPENAI_API_KEY not set")
     body = json.dumps({
     "model": model,
     "messages": [{"role": "user", "content": prompt}],
     }).encode("utf-8")
     req = urllib.request.Request(
     "https://api.openai.com/v1/chat/completions",
     data=body,
     headers={
     "Authorization": f"Bearer {api_key}",
     "Content-Type": "application/json",
     },
     )
     with urllib.request.urlopen(req, timeout=60) as resp:
         payload = json.loads(resp.read())
         return payload["choices"][0]["message"]["content"]
'''

SCANNER = '''"""Nmap wrapper producing structured host/port results."""

import os
import shutil
import subprocess
from dataclasses import dataclass, field

@dataclass
class Host:
 address: str
 ports: dict = field(default_factory=dict)

def _nmap_bin() -> str:
 return os.environ.get("NMAP_BIN", "nmap")

def _nmap_available() -> bool:
 return shutil.which(_nmap_bin()) is not None

def scan(targets: str, ports: str = "1-1000") -> list:
 """Run nmap and parse its greppable (-oG) output into Host objects."""
 if not _nmap_available():
     raise RuntimeError("nmap not on PATH -- install it or point NMAP_BIN at a binary")
     cmd = [_nmap_bin(), "-Pn", "-sT", "-oG", "-", "-p", ports, targets]
     proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, check=False)
     hosts = []
     for line in proc.stdout.splitlines():
         if "Ports:" not in line:
             continue
             head, _, tail = line.partition("Ports:")
             parts = head.split()
             address = parts[1]
             h = Host(address=address)
             for chunk in tail.strip().split(","):
                 bits = chunk.strip().split("/")
                 if len(bits) >= 5:
                     h.ports[int(bits[0])] = {"state": bits[1], "service": bits[4]}
                     hosts.append(h)
                     return hosts
'''

ORCHESTRATOR = '''"""Turn scanner output into a structured engagement report."""

from atmjack.scanner import Host

def build_report(hosts: list[Host]) -> dict:
 """Summarize discovered hosts and notable open ports."""
 report: dict = {"hosts": [], "access": []}
 report["hosts"] = [{"address": h.address, "ports": h.ports} for h in hosts]
 for h in hosts:
     if 445 in h.ports:
         report["access"].append({"host": h.address, "note": "SMB open"})
         if 3389 in h.ports:
             report["access"].append({"host": h.address, "note": "RDP open"})
             return report
'''

TOOLS = '''"""Tool registry dispatching to atmjack modules."""

from atmjack import access, creds, scanner

REGISTRY = {
 "scan": scanner.scan,
 "hydra": creds.hydra,
 "windapsearch": access.windapsearch,
}

def call(name: str, **kwargs):
 """Invoke a registered tool by name."""
 if name not in REGISTRY:
     raise KeyError(f"unknown tool: {name}")
     return REGISTRY[name](**kwargs)
'''

API = '''"""FastAPI surface for atmjack scans."""

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="atmjack")

def _now() -> str:
 return datetime.now(timezone.utc).isoformat()

class ScanState(str, enum.Enum):
 queued = "queued"
 running = "running"
 done = "done"
 failed = "failed"

@dataclass
class ScanRecord:
 scan_id: str
 target: str
 state: ScanState = ScanState.queued
 result: dict[str, Any] | None = None
 error: str | None = None
 created: str = field(default_factory=_now)
 updated: str = field(default_factory=_now)

_SCANS: dict[str, ScanRecord] = {}

def run_scan(target: str) -> dict[str, Any]:
 """Stub scan implementation until the scanner module lands."""
 now = _now()
 return {
 "scan_id": str(uuid.uuid4()),
 "target": target,
 "started": now,
 "ended": now,
 "modules": [{"name": "stub", "status": "ok", "duration_ms": 0}],
 "findings": [],
 }

def _execute(scan_id: str, target: str) -> None:
 rec = _SCANS.get(scan_id)
 if rec is None:
     return
     rec.state = ScanState.running
     rec.updated = _now()
     try:
         rec.result = run_scan(target)
         rec.state = ScanState.done
 except Exception as exc: # noqa: BLE001 - background task boundary
     rec.error = f"{type(exc).__name__}: {exc}"
     rec.state = ScanState.failed
 finally:
     rec.updated = _now()

def _get_scan(scan_id: str) -> ScanRecord:
 rec = _SCANS.get(scan_id)
 if rec is None:
     raise HTTPException(status_code=404, detail=f"scan {scan_id!r} not found")
     return rec

class ScanRequest(BaseModel):
 target: str

@app.post("/scans")
def start_scan(req: ScanRequest, background: BackgroundTasks) -> dict:
 rec = ScanRecord(scan_id=str(uuid.uuid4()), target=req.target)
 _SCANS[rec.scan_id] = rec
 background.add_task(_execute, rec.scan_id, rec.target)
 return {"scan_id": rec.scan_id, "state": rec.state.value}

@app.get("/scans/{scan_id}")
def get_scan(scan_id: str) -> dict:
 rec = _get_scan(scan_id)
 return {
 "scan_id": rec.scan_id,
 "target": rec.target,
 "state": rec.state.value,
 "result": rec.result,
 "error": rec.error,
 "created": rec.created,
 "updated": rec.updated,
 }
'''

UTILS_HELPERS = '''

def fix_path_string(path: str) -> str:
 """Local replacement for ScoutSuite.core.conditions.fix_path_string."""
 return path.replace("/", ".")

def pass_conditions(conditions, context=None) -> bool:
 """Minimal local replacement for ScoutSuite.core.conditions.pass_conditions."""
 if conditions is None:
     return True
     if isinstance(conditions, list):
         return all(pass_conditions(c, context) for c in conditions)
         return bool(conditions)

def print_exception(message: str, additional_details=None) -> None:
 """Local replacement for ScoutSuite.core.console.print_exception."""
 print(f"[!] {message}")
 if additional_details:
     print(f" {additional_details}")

def do_something_useful() -> None:
 """Placeholder invoked by cli.py."""
 print("atmjack ready")
'''

TEST_SNIPPET = """

def test_modules_import():
 import atmjack.access # noqa: F401
 import atmjack.api # noqa: F401
 import atmjack.creds # noqa: F401
 import atmjack.llm # noqa: F401
 import atmjack.orchestrator # noqa: F401
 import atmjack.scanner # noqa: F401
 import atmjack.tools # noqa: F401
"""


def write_module(name: str, content: str) -> None:
    path = SRC / name
    path.write_text(content, encoding="utf-8", newline="\n")
    print(f"rewrote {path.relative_to(ROOT)}")


def patch_utils() -> None:
    path = SRC / "utils.py"
    text = path.read_text(encoding="utf-8")

    # Drop the ScoutSuite imports (ty: import-not-found).
    lines = [ln for ln in text.splitlines() if not ln.startswith("from ScoutSuite")]

    # E721: use isinstance for type checks.
    fixed = []
    for ln in lines:
        ln = ln.replace("if type(current_info) == dict:", "if isinstance(current_info, dict):")
        ln = ln.replace("elif type(current_info) == list:", "elif isinstance(current_info, list):")
        fixed.append(ln)
        lines = fixed

    # E501: split the over-long f-string across two lines.
    out = []
    for ln in lines:
        if "Unable to recursively test condition" not in ln or len(ln) <= 120:
            out.append(ln)
            continue
            indent = ln[: len(ln) - len(ln.lstrip())]
            body = ln.strip()
            marker = ": unhandled case for"
            idx = body.find(marker)
            if idx == -1:
                out.append(ln)
                continue
                first = body[:idx] + ": '"
                second = "f'" + body[idx + 2 :]
                out.append(indent + first)
                out.append(indent + second)
                lines = out

    # Insert local helper replacements after the import block.
    if not any("def do_something_useful" in ln for ln in lines):
        last_import = 0
        for i, ln in enumerate(lines):
            if ln.startswith(("import ", "from ")):
                last_import = i
                lines.insert(last_import + 1, UTILS_HELPERS)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"patched {path.relative_to(ROOT)}")


def add_regression_test() -> None:
    path = ROOT / "tests" / "test_atmjack.py"
    current = path.read_text(encoding="utf-8")
    if "test_modules_import" in current:
        print("regression test already present")
        return
        path.write_text(current + TEST_SNIPPET, encoding="utf-8", newline="\n")
        print(f"appended test_modules_import to {path.relative_to(ROOT)}")


def run_checks() -> None:
    commands = [
        ["uv", "run", "python", "-m", "compileall", "-q", "src", "tests"],
        ["uv", "run", "ruff", "format", "."],
        ["uv", "run", "ruff", "check", "--fix", "."],
        ["uv", "run", "ty", "check", "."],
        ["uv", "run", "pytest"],
    ]
    for cmd in commands:
        print(f"\n==> {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=ROOT)
        if result.returncode != 0:
            sys.exit(f"FAILED ({result.returncode}): {' '.join(cmd)}")
            print("\nAll checks passed.")


def main() -> None:
    write_module("access.py", ACCESS)
    write_module("api.py", API)
    write_module("creds.py", CREDS)
    write_module("llm.py", LLM)
    write_module("orchestrator.py", ORCHESTRATOR)
    write_module("scanner.py", SCANNER)
    write_module("tools.py", TOOLS)
    patch_utils()
    add_regression_test()
    run_checks()


if __name__ == "__main__":
    main()
