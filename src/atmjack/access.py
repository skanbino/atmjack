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
