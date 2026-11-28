"""FastAPI surface for atmjack."""

from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel

from atmjack.models import ScanRecord, ScanState
from atmjack.orchestrator import run_scan
from atmjack.store import ScanStore

API_KEY = os.environ.get("ATMJACK_API_KEY")

app = FastAPI(title="atmjack", version="0.1.0")
store = ScanStore()

class ScanRequest(BaseModel):
 target: str
 ports: str = "1-1000"
 dry_run: bool = False
 use_llm: bool = True
 userlist: str | None = None
 passlist: str | None = None
 domain: str | None = None

def require_key(x_api_key: str | None = Header(default=None)) -> None:
 if API_KEY is None:
  return
 if x_api_key != API_KEY:
  raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")

@app.get("/healthz")
def healthz() -> dict[str, str]:
 return {"status": "ok"}

@app.get("/scans", dependencies=[Depends(require_key)])
def list_scans() -> list[dict[str, Any]]:
 return [record.to_dict() for record in store.list()]

@app.post("/scans", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_key)])
def create_scan(request: ScanRequest) -> dict[str, Any]:
 record = ScanRecord(target=request.target)
 store.add(record)
 try:
  result = run_scan(
   request.target,
   scan_id=record.scan_id,
   ports=request.ports,
   dry_run=request.dry_run,
   use_llm=request.use_llm,
   userlist=request.userlist,
   passlist=request.passlist,
   domain=request.domain,
  )
 except Exception as exc:
  store.update(record.scan_id, state=ScanState.failed, error=str(exc))
  return {"scan_id": record.scan_id, "state": ScanState.failed.value}
 store.update(record.scan_id, state=ScanState.done, result=result)
 return {"scan_id": record.scan_id, "state": ScanState.done.value}

@app.get("/scans/{scan_id}", dependencies=[Depends(require_key)])
def get_scan(scan_id: str) -> dict[str, Any]:
 record = store.get(scan_id)
 if record is None:
  raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found")
 return record.to_dict()