import pathlib

FILES = {}

FILES["src/atmjack/__init__.py"] = '''"""atmjack -- network recon + AI agent controller."""
__version__ = "0.1.0"
'''

FILES["src/atmjack/scanner.py"] = '''"""nmap-backed scanner -- one entry point, returns parsed hosts."""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field

@dataclass
class Host:
 address: str
 ports: dict = field(default_factory=dict)

def _nmap_available() -> bool:
 return shutil.which("nmap") is not None

def scan(targets: str, ports: str = "1-1000") -> list:
 if not _nmap_available():
 raise RuntimeError("nmap not on PATH -- install it or point NMAP_BIN at a binary")
 cmd = ["nmap", "-Pn", "-sT", "-oG", "-", "-p", ports, targets]
 proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, check=False)
 hosts = []
 for line in proc.stdout.splitlines():
 if "Ports:" not in line:
 continue
 head, _, tail = line.partition("Ports:")
 parts = head.split()
 address = parts[1] if len(parts) >= 2 else "unknown"
 h = Host(address=address)
 for chunk in tail.strip().split(","):
 bits = chunk.strip().split("/")
 if len(bits) >= 5:
 h.ports[int(bits[0])] = {"state": bits[1], "service": bits[4]}
 hosts.append(h)
 return hosts
'''

FILES["src/atmjack/creds.py"] = '''"""credential testing -- hydra for online, hashcat for offline."""
from __future__ import annotations

import shutil
import subprocess

def hydra(host: str, service: str, userlist: str, passlist: str) -> dict:
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

FILES["src/atmjack/access.py"] = '''"""post-discovery access checks -- impacket/ldap."""
from __future__ import annotations

import shutil
import subprocess

def ldap_enum(domain: str, dc: str, user: str, password: str) -> str:
 bin_path = shutil.which("windapsearch") or shutil.which("windapsearch.py")
 if not bin_path:
 raise RuntimeError("windapsearch not on PATH -- add _ref/windapsearch to PATH")
 cmd = [bin_path, "--dc-ip", dc, "-d", domain, "-u", user, "-p", password]
 proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
 return proc.stdout
'''

FILES["src/atmjack/llm.py"] = '''"""thin LLM wrapper -- pluggable backend, no framework."""
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
'''

FILES["src/atmjack/tools.py"] = '''"""Tool registry -- name to callable, so the agent can dispatch."""
from __future__ import annotations

from. import scanner, creds, access

REGISTRY = {
 "scan": scanner.scan,
 "hydra": creds.hydra,
 "ldap_enum": access.ldap_enum,
}

def call(name: str, **kwargs):
 if name not in REGISTRY:
 raise KeyError(f"unknown tool: {name}")
 return REGISTRY[name](**kwargs)
'''

FILES["src/atmjack/orchestrator.py"] = '''"""Ties scanner + creds + access into one flow."""
from __future__ import annotations


def run_engagement(targets: str, ports: str = "22,80,443,445,3389") -> dict:
 from. import scanner

 report = {"targets": targets, "hosts": [], "credentials": [], "access": []}
 hosts = scanner.scan(targets, ports)
 report["hosts"] = [{"address": h.address, "ports": h.ports} for h in hosts]
 for h in hosts:
 if 445 in h.ports:
 report["access"].append({"host": h.address, "note": "SMB open"})
 if 3389 in h.ports:
 report["access"].append({"host": h.address, "note": "RDP open"})
 return report
'''

FILES["src/atmjack/api.py"] = '''"""FastAPI surface -- POST /scan and POST /engagement."""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from. import scanner, orchestrator

app = FastAPI(title="atmjack")

class ScanRequest(BaseModel):
 targets: str
 ports: str = "1-1000"


class EngRequest(BaseModel):
 targets: str
 ports: str = "22,80,443,445,3389"

@app.post("/scan")
def scan_endpoint(req: ScanRequest) -> dict:
 hosts = scanner.scan(req.targets, req.ports)
 return {"hosts": [{"address": h.address, "ports": h.ports} for h in hosts]}


@app.post("/engagement")
def engagement_endpoint(req: EngRequest) -> dict:
 return orchestrator.run_engagement(req.targets, req.ports)
'''

for rel, content in FILES.items():
 p = pathlib.Path(rel)
 p.parent.mkdir(parents=True, exist_ok=True)
 p.write_text(content, encoding="utf-8")
 print("WROTE", p, len(content), "bytes")