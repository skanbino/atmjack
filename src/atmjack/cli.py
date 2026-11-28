"""atmjack command line interface."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from atmjack import __version__
from atmjack.orchestrator import run_scan

def build_parser() -> argparse.ArgumentParser:
 parser = argparse.ArgumentParser(prog="atmjack", description="ATM/AD recon pipeline")
 sub = parser.add_subparsers(dest="command", required=True)

 scan = sub.add_parser("scan", help="run a scan against a target")
 scan.add_argument("target", help="host, CIDR, or nmap target expression")
 scan.add_argument("--ports", default="1-1000")
 scan.add_argument("--dry-run", action="store_true", help="skip nmap and emit a stub host")
 scan.add_argument("--no-llm", action="store_true", help="skip the LLM summary stage")
 scan.add_argument("--userlist", help="path to a hydra user list")
 scan.add_argument("--passlist", help="path to a hydra password list")
 scan.add_argument("--domain", help="AD domain for windapsearch")
 scan.add_argument("--json", action="store_true", help="emit the raw report as JSON")

 sub.add_parser("version", help="print the version and exit")
 return parser

def _print_summary(result: dict[str, Any]) -> None:
 print(f"scan {result['scan_id']} -> {result['target']}")
 print(f"hosts: {len(result.get('hosts', []))} findings: {len(result.get('findings', []))}")
 for module in result.get("modules", []):
  line = f" [{module['status']}] {module['name']} ({module['duration_ms']}ms)"
  if "error" in module:
   line += f" -- {module['error']}"
  print(line)
 for finding in result.get("findings", []):
  print(f" * {finding}")
 if result.get("summary"):
  print()
  print(result["summary"])

def main(argv: list[str] | None = None) -> int:
 args = build_parser().parse_args(argv)

 if args.command == "version":
  print(f"atmjack {__version__}")
  return 0

 if args.command != "scan":
  return 1

 result = run_scan(
  args.target,
  ports=args.ports,
  dry_run=args.dry_run,
  use_llm=not args.no_llm,
  userlist=args.userlist,
  passlist=args.passlist,
  domain=args.domain,
  )

 if args.json:
  print(json.dumps(result, indent=2))
 else:
  _print_summary(result)
 return 0

if __name__ == "__main__":
 sys.exit(main())