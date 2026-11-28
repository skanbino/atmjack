"""Domain models for atmjack."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class ScanState(str, Enum):
 queued = "queued"
 running = "running"
 done = "done"
 failed = "failed"

@dataclass
class Host:
 address: str
 hostname: str | None = None
 ports: dict[int, dict[str, Any]] = field(default_factory=dict)

 def to_dict(self) -> dict[str, Any]:
  return {
   "address": self.address,
   "hostname": self.hostname,
   "ports": {str(port): info for port, info in self.ports.items()},
  }

@dataclass
class ScanRecord:
 scan_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
 target: str = ""
 state: ScanState = ScanState.queued
 result: dict[str, Any] | None = None
 error: str | None = None

 def to_dict(self) -> dict[str, Any]:
  return {
   "scan_id": self.scan_id,
   "target": self.target,
   "state": self.state.value,
   "result": self.result,
   "error": self.error,
  }