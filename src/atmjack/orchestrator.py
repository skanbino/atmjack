"""Ties scanner + creds + access into one flow."""
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
