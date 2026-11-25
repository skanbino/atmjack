"""HTTP surface for atmjack - FastAPI app with background scan tasks."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

try:
 from atmjack.scanner import run_scan
except ImportError: # fallback stub until scanner module lands
 def run_scan(target: str) -> dict[str, Any]:
 now = datetime.now(timezone.utc).isoformat()
 return {
 "scan_id": str(uuid.uuid4()),
 "target": target,
 "started": now,
 "ended": now,
 "modules": [{"name": "stub", "status": "ok", "duration_ms": 0}],
 "findings": [],
 }

class ScanState(str, Enum):
 queued = "queued"
 running = "running"
 done = "done"
 failed = "failed"

class ScanRequest(BaseModel):
 target: str = Field(..., min_length=1, max_length=253, examples=["192.168.56.10"])

class ScanAccepted(BaseModel):
 scan_id: str
 state: ScanState


class ScanRecord(BaseModel):
 scan_id: str
 target: str
 state: ScanState
 created: str
 updated: str
 result: dict[str, Any] | None = None
 error: str | None = None

_SCANS: dict[str, ScanRecord] = {}

def _now() -> str:
 return datetime.now(timezone.utc).isoformat()

def _execute(scan_id: str, target: str) -> None:
 rec = _SCANS.get(scan_id)
 if rec is None:
 return
 rec.state = ScanState.running
 rec.updated = _now()
 try:
 rec.result = run_scan(target)
 rec.state = ScanState.done
 except Exception as exc: # noqa: BLE001 - background task boundary
 rec.error = f"{type(exc).__name__}: {exc}"
 rec.state = ScanState.failed
 finally:
 rec.updated = _now()

app = FastAPI(title="atmjack", version="0.1.0")

@app.get("/healthz")
async def healthz() -> dict[str, str]:
 return {"status": "ok", "time": _now()}

@app.post("/scans", response_model=ScanAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_scan(req: ScanRequest, bg: BackgroundTasks) -> ScanAccepted:
 sid = uuid.uuid4().hex[:16]
 now = _now()
 _SCANS[sid] = ScanRecord(
 scan_id=sid, target=req.target, state=ScanState.queued, created=now, updated=now
 )
 bg.add_task(_execute, sid, req.target)
 return ScanAccepted(scan_id=sid, state=ScanState.queued)

@app.get("/scans", response_model=list[ScanRecord])
async def list_scans() -> list[ScanRecord]:
 return list(_SCANS.values())

@app.get("/scans/{scan_id}", response_model=ScanRecord)
async def get_scan(scan_id: str) -> ScanRecord:
 rec = _SCANS.get(scan_id)
 if rec is None:
 raise HTTPException(status_code=404, detail=f"scan {scan_id!r} not found")
 return rec