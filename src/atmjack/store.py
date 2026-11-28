"""JSON-backed scan store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from atmjack.models import ScanRecord, ScanState

class ScanStore:
 def __init__(self, path: Path | str | None = None) -> None:
  self.path = Path(path) if path is not None else None
  self._records: dict[str, ScanRecord] = {}
  if self.path is not None and self.path.exists():
   self._load()

 def _load(self) -> None:
  raw = json.loads(self.path.read_text(encoding="utf-8"))
  for item in raw:
   record = ScanRecord(
    scan_id=item["scan_id"],
    target=item["target"],
    state=ScanState(item["state"]),
    result=item.get("result"),
    error=item.get("error"),
   )
   self._records[record.scan_id] = record

 def _save(self) -> None:
  if self.path is None:
   return
  payload = [record.to_dict() for record in self._records.values()]
  self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

 def add(self, record: ScanRecord) -> ScanRecord:
  self._records[record.scan_id] = record
  self._save()
  return record

 def get(self, scan_id: str) -> ScanRecord | None:
  return self._records.get(scan_id)

 def list(self) -> list[ScanRecord]:
  return list(self._records.values())

 def update(self, scan_id: str, **fields: Any) -> ScanRecord | None:
  record = self._records.get(scan_id)
  if record is None:
   return None
  for key, value in fields.items():
   setattr(record, key, value)
  self._save()
  return record

 def clear(self) -> None:
  self._records.clear()
  self._save()