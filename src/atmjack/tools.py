# Subprocess wrappers for external tooling (hydra, windapsearch).

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any


_HYDRA_HIT = re.compile(r"^\[(?P<port>\d+)\]\[(?P<svc>[^\]]+)\]\s+host:\s+(?P<host>\S+)\s+login:\s+(?P<login>\S+)\s+password:\s+(?P<password>.+)$")
_WINDAP_ENTRY = re.compile(r"^(?P<attr>cn|sAMAccountName|userPrincipalName|memberOf|distinguishedName|mail):\s+(?P<value>.+)$", re.IGNORECASE)


def _have(binary: str) -> bool:
    return shutil.which(binary) is not None


def parse_hydra(stdout: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for raw in stdout.splitlines():
        line = raw.strip()
        match = _HYDRA_HIT.match(line)
        if not match:
            continue
        hits.append({
            "host": match.group("host"),
            "port": int(match.group("port")),
            "service": match.group("svc"),
            "login": match.group("login"),
            "password": match.group("password"),
        })
    return hits


def run_hydra(target: str, userlist: str, passlist: str, service: str = "smb", port: int = 445, timeout: int = 600) -> list[dict[str, Any]]:
    if not _have("hydra"):
        raise RuntimeError("hydra binary not found on PATH")
    cmd = [
        "hydra",
        "-L", userlist,
        "-P", passlist,
        "-s", str(port),
        "-t", "4",
        "-f",
        target,
        service,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    hits = parse_hydra(result.stdout)
    parsed_errors = [line for line in result.stdout.splitlines() if "ERROR" in line.upper()]
    if not hits and parsed_errors:
        raise RuntimeError(f"hydra produced no hits; last error line: {parsed_errors[-1]}")
    return hits

def parse_windap(stdout: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue
        match = _WINDAP_ENTRY.match(line)
        if not match:
            continue
        attr = match.group("attr").lower()
        value = match.group("value").strip()
        if attr == "memberof" and attr in current:
            current[attr].append(value)
        elif attr == "memberof":
            current[attr] = [value]
        else:
            current[attr] = value
    if current:
        entries.append(current)
    return entries

def run_windap(target: str, domain: str, username: str | None = None, password: str | None = None, timeout: int = 300) -> list[dict[str, Any]]:
    if not _have("windapsearch"):
        raise RuntimeError("windapsearch binary not found on PATH")
    cmd = ["windapsearch", "--dc-ip", target, "-d", domain, "--users"]
    if username and password:
        cmd.extend(["-u", username, "-p", password])
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    entries = parse_windap(result.stdout)
    if not entries and "error" in result.stdout.lower():
        raise RuntimeError(f"windapsearch returned no users; stderr: {result.stderr.strip()[:200]}")
    return entries
