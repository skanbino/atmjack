"""Credential brute-forcing via hydra."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

HYDRA_BIN = "hydra"

def hydra(
 host: str,
 service: str,
 userlist: str,
 passlist: str,
 *,
 timeout: int = 3600,
) -> dict[str, Any]:
 """Run hydra against a single host/service and return the matching lines."""
 if not shutil.which(HYDRA_BIN):
 raise RuntimeError("hydra not on PATH")
 cmd = [HYDRA_BIN, "-L", userlist, "-P", passlist, "-I", "-f", f"{service}://{host}"]
 proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
 found = [line.strip() for line in proc.stdout.splitlines() if "password:" in line.lower()]
 return {"found": found, "raw": proc.stdout, "returncode": proc.returncode}