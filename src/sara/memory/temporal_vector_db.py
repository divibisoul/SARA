"""SARA — Memória: TemporalVectorDB (índice temporal + vetorial).
Status: IMPLEMENTED
"""
from __future__ import annotations
import math
import json
import os
import threading
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any, Optional
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.hashing import short_hash
from sara.infra.clock import now_iso


@dataclass
class Record:
    id: str
    data: dict
    ts: str
    inserted_at: str
    vector: Optional[list[float]] = None
    integrity: str = ""


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class TemporalVectorDB:
    NAME = "TemporalVectorDB"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.MEMORY
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.PERSISTENCE,)

    def __init__(self, persist_path: str | None = None) -> None:
        self._records: list[Record] = []
        self._persist_path = (persist_path or os.getenv("SARA_TEMPORAL_PERSIST_PATH", "")).strip() or None
        self._lock = threading.RLock()

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "persistence_enabled": self._persist_path is not None,
            "persistence_path": self._persist_path,
        }

    def insert(self, data: dict, ts: Optional[str] = None,
               vector: Optional[list[float]] = None) -> str:
        ts_val = ts or now_iso()
        rid = short_hash({"data": data, "ts": ts_val})
        integrity = short_hash({"id": rid, "data": data, "ts": ts_val, "vector": vector})
        with self._lock:
            self._records.append(
                Record(id=rid, data=dict(data), ts=ts_val,
                       inserted_at=now_iso(), vector=vector, integrity=integrity)
            )
        return rid

    def by_id(self, record_id: str) -> Optional[Record]:
        for r in self._records:
            if r.id == record_id:
                return r
        return None

    def by_time_range(self, start: str, end: str) -> list[Record]:
        return [r for r in self._records if start <= r.ts <= end]

    def by_vector(self, query_vec: list[float], top_k: int = 5) -> list[tuple[Record, float]]:
        scored = [
            (r, _cosine(query_vec, r.vector))
            for r in self._records
            if r.vector is not None
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def by_data(self, filters: dict[str, Any]) -> list[Record]:
        return [
            r for r in self._records
            if all(r.data.get(key) == value for key, value in filters.items())
        ]

    def verify_record(self, record_id: str) -> bool:
        record = self.by_id(record_id)
        if record is None:
            return False
        expected = short_hash({
            "id": record.id,
            "data": record.data,
            "ts": record.ts,
            "vector": record.vector,
        })
        return record.integrity == expected

    def count(self) -> int:
        return len(self._records)

    def all_sorted(self) -> list[Record]:
        return sorted(self._records, key=lambda r: r.ts)

    def persist(self, path: str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            payload = [asdict(r) for r in self._records]
        tmp = target.with_name(target.name + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, target)

    def persist_if_configured(self) -> bool:
        if not self._persist_path:
            return False
        self.persist(self._persist_path)
        return True

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, list):
            raise ValueError("TEMPORAL_VECTOR_PAYLOAD_INVALID")
        loaded: list[Record] = []
        for item in payload:
            if not isinstance(item, dict) or not item.get("integrity"):
                raise ValueError("TEMPORAL_VECTOR_INTEGRITY_MISSING")
            record = Record(**item)
            if not self.verify_record_payload(record):
                raise ValueError("TEMPORAL_VECTOR_INTEGRITY_FAILED")
            loaded.append(record)
        with self._lock:
            self._records = loaded

    def verify_record_payload(self, record: Record) -> bool:
        expected = short_hash({
            "id": record.id,
            "data": record.data,
            "ts": record.ts,
            "vector": record.vector,
        })
        return record.integrity == expected

    def load_if_configured(self) -> bool:
        if not self._persist_path or not Path(self._persist_path).exists():
            return False
        self.load(self._persist_path)
        return True

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("persistence", self.NAME, True,
                       total_records=self.count())