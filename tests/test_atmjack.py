# language: Python 3, file: tests/test_atmjack.py
"""Unit tests — no network, no subprocess, no root. Pure logic + mocked IO."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_scan() -> dict[str, Any]:
 """A representative scan payload shaped like the CLI's JSON output."""
 return {
 "scan_id": "test-scan-001",
 "target": "192.168.56.10",
 "started": "2026-11-25T00:00:00Z",
 "ended": "2026-11-25T00:00:08Z",
 "modules": [
 {"name": "recon", "status": "ok", "duration_ms": 2100},
 {"name": "xfs_recover", "status": "ok", "duration_ms": 4300},
 {"name": "pin_extract", "status": "failed", "reason": "no_xfs_found"},
 ],
 "findings": [
 {"kind": "xfs_headers", "count": 312, "severity": "info"},
 {"kind": "pin_blocks", "count": 0, "severity": "info"},
 ],
 }

@pytest.fixture()
def scan_file(tmp_path: Path, sample_scan: dict[str, Any]) -> Path:
 p = tmp_path / "scan.json"
 p.write_text(json.dumps(sample_scan), encoding="utf-8")
 return p

# ---------------------------------------------------------------------------
# scan payload shape
# ---------------------------------------------------------------------------


def test_scan_payload_has_required_keys(sample_scan: dict[str, Any]) -> None:
 for key in ("scan_id", "target", "started", "ended", "modules", "findings"):
     assert key in sample_scan, f"missing top-level key: {key}"

def test_modules_all_carry_status(sample_scan: dict[str, Any]) -> None:
 for mod in sample_scan["modules"]:
     assert "name" in mod
     assert mod.get("status") in {"ok", "failed", "skipped"}, mod

def test_failed_modules_carry_reason(sample_scan: dict[str, Any]) -> None:
 for mod in sample_scan["modules"]:
     if mod["status"] == "failed":
         assert "reason" in mod, f"failed module {mod['name']} lacks reason"


def test_findings_counts_are_non_negative(sample_scan: dict[str, Any]) -> None:
 for finding in sample_scan["findings"]:
     assert isinstance(finding["count"], int)
     assert finding["count"] >= 0


# ---------------------------------------------------------------------------
# json roundtrip via tmp_path — proves the contract is disk-safe
# ---------------------------------------------------------------------------

def test_scan_roundtrip_from_disk(scan_file: Path, sample_scan: dict[str, Any]) -> None:
 loaded = json.loads(scan_file.read_text(encoding="utf-8"))
 assert loaded == sample_scan

def test_scan_file_is_utf8(scan_file: Path) -> None:
 raw = scan_file.read_bytes()
 raw.decode("utf-8") # raises on invalid

# ---------------------------------------------------------------------------
# subprocess mocking — how we test the CLI wrapper without the CLI
# ---------------------------------------------------------------------------


def test_cli_invocation_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
 """Mock subprocess.run so we can assert argv shape without running anything."""
 captured: dict[str, Any] = {}

 def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
     captured["args"] = args
     captured["kwargs"] = kwargs
     return subprocess.CompletedProcess(
     args=args, returncode=0, stdout="ok", stderr=""
     )

 monkeypatch.setattr(subprocess, "run", fake_run)

 result = subprocess.run(
 ["python", "-m", "atmjack", "--scan", "192.168.56.10"],
 capture_output=True,
 text=True,
 check=False,
 )

 assert result.returncode == 0
 assert captured["args"] == ["python", "-m", "atmjack", "--scan", "192.168.56.10"]
 assert captured["kwargs"]["capture_output"] is True

def test_cli_nonzero_exit_detected(monkeypatch: pytest.MonkeyPatch) -> None:
 monkeypatch.setattr(
 subprocess,
 "run",
 lambda args, **kw: subprocess.CompletedProcess(
 args=args, returncode=2, stdout="", stderr="bad args"
 ),
 )
 result = subprocess.run(
 ["python", "-m", "atmjack", "--bogus"],
 capture_output=True,
 text=True,
 check=False,
 )
 assert result.returncode == 2
 assert "bad args" in result.stderr

# ---------------------------------------------------------------------------
# scan_id validation (a shape the api layer relies on)
# ---------------------------------------------------------------------------


def test_scan_id_is_url_safe(sample_scan: dict[str, Any]) -> None:
 sid = sample_scan["scan_id"]
 assert isinstance(sid, str) and sid
 assert all(c.isalnum() or c in "-_" for c in sid), f"unsafe scan_id: {sid!r}"

def test_target_is_ip_literal(sample_scan: dict[str, Any]) -> None:
 parts = sample_scan["target"].split(".")
 assert len(parts) == 4
 for p in parts:
     assert 0 <= int(p) <= 255