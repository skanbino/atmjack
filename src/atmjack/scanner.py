"""nmap wrapper and greppable-output parser."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

from atmjack.models import Host

def parse_greppable(text: str) -> list[Host]:
 hosts: list[Host] = []
 for line in text.splitlines():
  if not line.startswith("Host: "):
   continue
  body = line[len("Host: "):]
  address_part, _, rest = body.partition("\t")
  address = address_part.split(" ")[0]
  hostname = None
  if "(" in address_part and ")" in address_part:
   hostname = address_part[address_part.index("(") + 1:address_part.index(")")]
  ports: dict[int, dict[str, Any]] = {}
  if "Ports: " in rest:
   port_section = rest.split("Ports: ", 1)[1]
   for entry in port_section.split(", "):
    parts = entry.split("/")
    if len(parts) < 5:
     continue
    try:
     port = int(parts[0])
    except ValueError:
     continue
    ports[port] = {"state": parts[1], "proto": parts[2], "service": parts[4]}
  hosts.append(Host(address=address, hostname=hostname, ports=ports))
 return hosts

def scan(target: str, ports: str = "1-1000", dry_run: bool = False) -> list[Host]:
 if dry_run or shutil.which("nmap") is None:
  return [Host(address=target)]
 cmd = ["nmap", "-Pn", "-p", ports, "-oG", "-", target]
 proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
 return parse_greppable(proc.stdout)