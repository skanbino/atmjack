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
