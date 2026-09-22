"""SARA — Monitoramento: DecisionTrace v2.
Status: IMPLEMENTED (cadeia local thread-safe) | PENDING (IPFS).
"""
from __future__ import annotations
import threading
from dataclasses import dataclass
from typing import Optional
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.hashing import chain_hash
from sara.infra.clock import now_iso


@dataclass
class TraceEntry:
    index: int
    ts: str
    decision: dict
    prev_hash: str
    hash: str


class DecisionTrace:
    NAME = "DecisionTrace"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.MONITORING
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.MONITORING, CyclePhase.PERSISTENCE)

    def __init__(self) -> None:
        self._entries: list[TraceEntry] = []
        self._lock = threading.RLock()

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "ipfs_ready": self.is_ipfs_ready(),
        }

    def log(self, decision: dict) -> TraceEntry:
        with self._lock:
            prev = self._entries[-1].hash if self._entries else "GENESIS"
            h = chain_hash(prev, decision)
            entry = TraceEntry(
                index=len(self._entries),
                ts=now_iso(),
                decision=dict(decision),
                prev_hash=prev,
                hash=h,
            )
            self._entries.append(entry)
            return entry

    def verify(self) -> bool:
        with self._lock:
            prev = "GENESIS"
            for e in self._entries:
                expected = chain_hash(prev, e.decision)
                if expected != e.hash:
                    return False
                prev = e.hash
            return True

    def query(self, filters: Optional[dict] = None) -> list[TraceEntry]:
        with self._lock:
            if not filters:
                return list(self._entries)
            return [e for e in self._entries
                    if all(e.decision.get(k) == v for k, v in filters.items())]

    def is_ipfs_ready(self) -> bool:
        return False

    def publish_to_ipfs(self, entry: TraceEntry) -> str:
        raise NotImplementedError(
            "DecisionTrace.publish_to_ipfs requer nó IPFS ou gateway configurado. "
            "Nenhum backend IPFS está disponível. "
            "Ativação: ver CANONICAL_ACTIVATION_PLAN.for_module('DecisionTrace')."
        )

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("monitoring", self.NAME, True,
                       total_entries=len(self._entries))