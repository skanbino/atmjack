"""FastAPI surface -- POST /scan and POST /engagement."""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from. import scanner, orchestrator

app = FastAPI(title="atmjack")

class ScanRequest(BaseModel):
 targets: str
 ports: str = "1-1000"


class EngRequest(BaseModel):
 targets: str
 ports: str = "22,80,443,445,3389"

@app.post("/scan")
def scan_endpoint(req: ScanRequest) -> dict:
 hosts = scanner.scan(req.targets, req.ports)
 return {"hosts": [{"address": h.address, "ports": h.ports} for h in hosts]}


@app.post("/engagement")
def engagement_endpoint(req: EngRequest) -> dict:
 return orchestrator.run_engagement(req.targets, req.ports)
