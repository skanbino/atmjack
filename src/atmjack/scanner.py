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
