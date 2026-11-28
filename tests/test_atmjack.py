"""Regression and behaviour tests for atmjack."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient

from atmjack import api, cli, orchestrator, scanner, utils
from atmjack.models import Host, ScanRecord, ScanState
from atmjack.store import ScanStore

NMAP_GREP = (
 "# Nmap 7.94 scan initiated\n"
 "Host: 10.0.0.1 (dc01.lab)\tPorts: 22/open/tcp//ssh///, 445/open/tcp//microsoft-ds///, "
 "3389/open/tcp//ms-wbt-server///\n"
 "Host: 10.0.0.2 (ws01.lab)\tPorts: 80/open/tcp//http///\n"
)

@dataclass
class Cfg:
 conditions: Any = None
 checked_items: int = 0
 id_suffix: str = field(default="")

@pytest.fixture(autouse=True)
def _isolate_api(monkeypatch: pytest.MonkeyPatch) -> Any:
 monkeypatch.setattr(api, "API_KEY", None)
 api.store.clear()
 yield
 api.store.clear()

def test_parse_greppable_extracts_hosts_and_ports() -> None:
 hosts = scanner.parse_greppable(NMAP_GREP)
 assert [h.address for h in hosts] == ["10.0.0.1", "10.0.0.2"]
 assert hosts[0].ports[445]["service"] == "microsoft-ds"
 assert hosts[1].ports[80]["state"] == "open"

def test_parse_greppable_ignores_junk_lines() -> None:
 out = scanner.parse_greppable("garbage\nHost: 1.2.3.4\tPorts: 22/open/tcp//ssh///\n")
 assert out[0].address == "1.2.3.4"

def test_build_report_flags_smb_and_rdp() -> None:
 hosts = [
  Host(
   address="10.0.0.1",
   ports={
    445: {"state": "open", "service": "smb"},
    3389: {"state": "open", "service": "rdp"},
   },
  )
 ]
 notes = {entry["note"] for entry in orchestrator.build_report(hosts)["access"]}
 assert notes == {"SMB open", "RDP open"}

def test_run_scan_dry_run_shape() -> None:
 result = orchestrator.run_scan("10.0.0.0/24", dry_run=True, use_llm=False)
 assert {"scan_id", "target", "started", "ended", "modules", "findings"} <= set(result)
 assert result["target"] == "10.0.0.0/24"
 assert any(m["name"] == "scanner" for m in result["modules"])

def test_run_scan_records_module_failure(monkeypatch: pytest.MonkeyPatch) -> None:
 def boom(*_args: Any, **_kwargs: Any) -> list[Host]:
  raise RuntimeError("nmap exploded")

 monkeypatch.setattr(orchestrator.scanner, "scan", boom)
 result = orchestrator.run_scan("10.0.0.1", use_llm=False)
 stage = next(m for m in result["modules"] if m["name"] == "scanner")
 assert stage["status"] == "error"
 assert "nmap exploded" in stage["error"]

def test_run_scan_survives_missing_llm_key(monkeypatch: pytest.MonkeyPatch) -> None:
 monkeypatch.delenv("OPENAI_API_KEY", raising=False)
 result = orchestrator.run_scan("10.0.0.1", dry_run=True, use_llm=True)
 stage = next(m for m in result["modules"] if m["name"] == "llm")
 assert stage["status"] == "error"
 assert result["summary"] is None

def test_scan_state_transitions() -> None:
 record = ScanRecord(scan_id="x", target="t")
 assert record.state is ScanState.queued
 record.state = ScanState.running
 record.state = ScanState.done
 assert record.to_dict()["state"] == "done"

def test_store_roundtrip(tmp_path: Any) -> None:
 path = tmp_path / "scans.json"
 store = ScanStore(path)
 store.add(ScanRecord(scan_id="abc", target="10.0.0.1"))
 store.update("abc", state=ScanState.done, result={"ok": True})

 reloaded = ScanStore(path)
 got = reloaded.get("abc")
 assert got is not None
 assert got.state is ScanState.done
 assert got.result == {"ok": True}

def test_store_missing_returns_none(tmp_path: Any) -> None:
 assert ScanStore(tmp_path / "nope.json").get("zzz") is None

def test_store_update_missing_returns_none() -> None:
 assert ScanStore().update("nope", state=ScanState.done) is None

def test_pass_conditions_ops() -> None:
 info = {"a": {"b": 5}}
 assert utils.pass_conditions(info, [], {"path": "a.b", "op": "eq", "value": 5})
 assert not utils.pass_conditions(info, [], {"path": "a.b", "op": "gt", "value": 9})
 assert utils.pass_conditions(info, [], [{"path": "a.b", "op": "exists"}])
 assert utils.pass_conditions(info, [], None)
 assert not utils.pass_conditions(info, [], {"path": "a.z", "op": "exists"})

def test_fix_path_string() -> None:
 assert utils.fix_path_string({}, [], "a/b/c") == "a.b.c"

def test_get_keys_walks_dict_and_list() -> None:
 assert utils.get_keys(["a", "b"], Cfg(), all_info={"a": {"b": 1}}) == ["a.b"]
 assert utils.get_keys(["a", "b"], Cfg(), all_info={"a": [{"b": 1}, {"b": 2}]}) == [
  "a.0.b",
  "a.1.b",
 ]
 assert utils.get_keys(["a", "z"], Cfg(), all_info={"a": {"b": 1}}) == []


def test_api_create_and_get(monkeypatch: pytest.MonkeyPatch) -> None:
 monkeypatch.setattr(
  api,
  "run_scan",
  lambda target, **_kw: {"scan_id": "s", "target": target, "modules": [], "findings": []},
 )
 client = TestClient(api.app)
 created = client.post("/scans", json={"target": "10.0.0.1", "dry_run": True})
 assert created.status_code == 202

 scan_id = created.json()["scan_id"]
 fetched = client.get(f"/scans/{scan_id}")
 assert fetched.status_code == 200
 assert fetched.json()["state"] == "done"

def test_api_404_for_unknown_scan() -> None:
 assert TestClient(api.app).get("/scans/nope").status_code == 404

def test_api_key_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
 monkeypatch.setattr(api, "API_KEY", "secret")
 client = TestClient(api.app)
 assert client.get("/scans").status_code == 401
 assert client.get("/scans", headers={"X-API-Key": "secret"}).status_code == 200

def test_api_marks_failed_scan(monkeypatch: pytest.MonkeyPatch) -> None:
 def boom(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
  raise RuntimeError("kaboom")

 monkeypatch.setattr(api, "run_scan", boom)
 client = TestClient(api.app)
 scan_id = client.post("/scans", json={"target": "10.0.0.1"}).json()["scan_id"]
 body = client.get(f"/scans/{scan_id}").json()
 assert body["state"] == "failed"
 assert "kaboom" in body["error"]

def test_healthz() -> None:
 assert TestClient(api.app).get("/healthz").json()["status"] == "ok"

def test_cli_parser_scan_defaults() -> None:
 args = cli.build_parser().parse_args(["scan", "10.0.0.1"])
 assert args.target == "10.0.0.1"
 assert args.ports == "1-1000"
 assert args.dry_run is False

def test_cli_dry_run_json(capsys: pytest.CaptureFixture[str]) -> None:
 assert cli.main(["scan", "10.0.0.1", "--dry-run", "--no-llm", "--json"]) == 0
 assert '"target": "10.0.0.1"' in capsys.readouterr().out