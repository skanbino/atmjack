"""post-discovery access checks -- impacket/ldap."""
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
