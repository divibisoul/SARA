"""SARA — Segurança: EmergencyRollback.
Status: IMPLEMENTED
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Literal
import copy
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.hashing import chain_hash
from sara.infra.clock import now_iso


@dataclass(frozen=True)
class RollbackRecord:
    snapshot_hash: str
    label: str
    scope: str
    ts: str


@dataclass
class RollbackResult:
    restored: bool
    state: Optional[Any] = None
    reason: str = ""


class EmergencyRollback:
    NAME = "EmergencyRollback"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.SECURITY
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.SNAPSHOT,)

    def __init__(self) -> None:
        self._snapshots: dict[str, dict] = {}
        self._history: list[RollbackRecord] = []
        self._chain: list[str] = []

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
        }

    def _append_chain(self, h: str) -> str:
        prev = self._chain[-1] if self._chain else "GENESIS"
        ch = chain_hash(prev, h)
        self._chain.append(ch)
        return ch

    def capture(self, label: str, state: Any,
                scope: Literal["cycle", "full"] = "cycle") -> str:
        h = chain_hash(label + scope, state)
        self._snapshots[h] = {
            "label": label,
            "scope": scope,
            "state": copy.deepcopy(state),
            "ts": now_iso(),
        }
        self._append_chain(h)
        return h

    def restore(self, snapshot_hash: str) -> RollbackResult:
        if snapshot_hash not in self._snapshots:
            return RollbackResult(False, reason="hash_not_found")
        entry = self._snapshots[snapshot_hash]
        self._history.append(RollbackRecord(
            snapshot_hash=snapshot_hash,
            label=entry["label"],
            scope=entry["scope"],
            ts=now_iso(),
        ))
        return RollbackResult(True, state=copy.deepcopy(entry["state"]))

    def verify_chain(self) -> bool:
        prev = "GENESIS"
        for h in self._chain:
            expected = chain_hash(prev, h)
            if expected != h:
                return False
            prev = h
        return True

    def history(self) -> list[RollbackRecord]:
        return list(self._history)

    def snapshot_count(self) -> int:
        return len(self._snapshots)

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("snapshot", self.NAME, True,
                       snapshot_count=self.snapshot_count(),
                       chain_valid=self.verify_chain())