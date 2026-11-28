"""Active Directory enumeration via windapsearch."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

WINDAPSEARCH_BIN = "windapsearch"

def _available() -> bool:
 return shutil.which(WINDAPSEARCH_BIN) is not None

def windapsearch(
 domain: str,
 *,
 dc: str | None = None,
 module: str = "users",
 timeout: int = 300,
) -> dict[str, Any]:
 """Run a single windapsearch module against `domain`."""
 if not _available():
 raise RuntimeError("windapsearch not on PATH -- add _ref/windapsearch to PATH")
 cmd = [WINDAPSEARCH_BIN, "--domain", domain, f"--{module}"]
 if dc:
 cmd += ["--dc", dc]
 proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
 return {
 "module": module,
 "domain": domain,
 "raw": proc.stdout,
 "returncode": proc.returncode,
 }