from atmjack.scanner import Host


def build_report(hosts: list[Host]) -> dict:
    """Summarize discovered hosts and notable open ports."""
    report: dict = {"hosts": [], "access": []}
    report["hosts"] = [{"address": h.address, "ports": h.ports} for h in hosts]
    for h in hosts:
        if 445 in h.ports:
            report["access"].append({"host": h.address, "note": "SMB open"})
        if 3389 in h.ports:
            report["access"].append({"host": h.address, "note": "RDP open"})
    return report
