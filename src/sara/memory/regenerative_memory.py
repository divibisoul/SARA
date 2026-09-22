"""SARA — Memória: RegenerativeMemory (versionada).
Status: IMPLEMENTED
"""
from __future__ import annotations
import copy
import json
from dataclasses import dataclass, asdict
from typing import Any, Optional
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.hashing import short_hash
from sara.infra.clock import now_iso


@dataclass
class VersionRecord:
    id: int
    label: str
    state: dict
    ts: str
    integrity: str


class RegenerativeMemory:
    NAME = "RegenerativeMemory"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.MEMORY
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.PERSISTENCE,)

    def __init__(self) -> None:
        self._versions: list[VersionRecord] = []
        self._counter = 0

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
        }

    def store(self, state: dict, label: str = "") -> VersionRecord:
        self._counter += 1
        integrity = short_hash(state)
        v = VersionRecord(
            id=self._counter,
            label=label,
            state=copy.deepcopy(state),
            ts=now_iso(),
            integrity=integrity,
        )
        self._versions.append(v)
        return v

    def get(self, version_id: int) -> Optional[VersionRecord]:
        for v in self._versions:
            if v.id == version_id:
                return v
        return None

    def latest(self) -> Optional[VersionRecord]:
        return self._versions[-1] if self._versions else None

    def diff(self, v1_id: int, v2_id: int) -> dict:
        v1 = self.get(v1_id)
        v2 = self.get(v2_id)
        if not v1 or not v2:
            return {"error": "version_not_found"}
        return {
            "same_integrity": v1.integrity == v2.integrity,
            "v1_len": len(str(v1.state)),
            "v2_len": len(str(v2.state)),
        }

    def trail(self) -> list[VersionRecord]:
        return list(self._versions)

    def persist(self, path: str) -> None:
        payload = [asdict(v) for v in self._versions]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        self._versions = [VersionRecord(**p) for p in payload]
        self._counter = max((v.id for v in self._versions), default=0)

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("persistence", self.NAME, True,
                       total_versions=len(self._versions))