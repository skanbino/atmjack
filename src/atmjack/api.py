import enum
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="atmjack")


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ScanState(enum.StrEnum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


@dataclass
class ScanRecord:
    scan_id: str
    target: str
    state: ScanState = ScanState.queued
    result: dict[str, Any] | None = None
    error: str | None = None
    created: str = field(default_factory=_now)
    updated: str = field(default_factory=_now)


_SCANS: dict[str, ScanRecord] = {}


def run_scan(target: str) -> dict[str, Any]:
    """Stub scan implementation until the scanner module lands."""
    now = _now()
    return {
        "scan_id": str(uuid.uuid4()),
        "target": target,
        "started": now,
        "ended": now,
        "modules": [{"name": "stub", "status": "ok", "duration_ms": 0}],
        "findings": [],
    }


def _execute(scan_id: str, target: str) -> None:
    rec = _SCANS.get(scan_id)
    if rec is None:
        return
    rec.state = ScanState.running
    rec.updated = _now()
    try:
        rec.result = run_scan(target)
        rec.state = ScanState.done
    except Exception as exc:  # noqa: BLE001 - background task boundary
        rec.error = f"{type(exc).__name__}: {exc}"
        rec.state = ScanState.failed
    finally:
        rec.updated = _now()


def _get_scan(scan_id: str) -> ScanRecord:
    rec = _SCANS.get(scan_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"scan {scan_id!r} not found")
    return rec


class ScanRequest(BaseModel):
    target: str


@app.post("/scans")
def start_scan(req: ScanRequest, background: BackgroundTasks) -> dict:
    rec = ScanRecord(scan_id=str(uuid.uuid4()), target=req.target)
    _SCANS[rec.scan_id] = rec
    background.add_task(_execute, rec.scan_id, rec.target)
    return {"scan_id": rec.scan_id, "state": rec.state.value}


@app.get("/scans/{scan_id}")
def get_scan(scan_id: str) -> dict:
    rec = _get_scan(scan_id)
    return {
        "scan_id": rec.scan_id,
        "target": rec.target,
        "state": rec.state.value,
        "result": rec.result,
        "error": rec.error,
        "created": rec.created,
        "updated": rec.updated,
    }
