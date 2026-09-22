"""SARA — Memória: TemporalVectorDB (índice temporal + vetorial).
Status: IMPLEMENTED
"""
from __future__ import annotations
import math
import json
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

    def __init__(self) -> None:
        self._records: list[Record] = []

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
        }

    def insert(self, data: dict, ts: Optional[str] = None,
               vector: Optional[list[float]] = None) -> str:
        ts_val = ts or now_iso()
        rid = short_hash({"data": data, "ts": ts_val})
        self._records.append(
            Record(id=rid, data=dict(data), ts=ts_val,
                   inserted_at=now_iso(), vector=vector)
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

    def count(self) -> int:
        return len(self._records)

    def all_sorted(self) -> list[Record]:
        return sorted(self._records, key=lambda r: r.ts)

    def persist(self, path: str) -> None:
        payload = [asdict(r) for r in self._records]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        self._records = [Record(**p) for p in payload]

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("persistence", self.NAME, True,
                       total_records=self.count())