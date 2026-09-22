"""SARA — Meta: QuantumSnapshotSystem.
Status: IMPLEMENTED
Nome histórico preservado. Não há mecanismo quântico físico.
"""
from __future__ import annotations
import copy
from dataclasses import dataclass
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.hashing import short_hash
from sara.infra.clock import now_iso
from sara.infra.hashing import chain_hash


@dataclass
class SnapshotMetadata:
    id: str
    ts: str
    size: int
    integrity: str = ""


class QuantumSnapshotSystem:
    NAME = "QuantumSnapshotSystem"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.SNAPSHOT,)

    def __init__(self) -> None:
        self._snapshots: dict[str, dict] = {}
        self._chain: list[str] = []

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "snapshot_count": len(self._snapshots),
        }

    def snapshot(self, state: dict) -> str:
        sid = short_hash({"state": state, "ts": now_iso()})
        ts = now_iso()
        snapshot_hash = chain_hash(
            self._chain[-1] if self._chain else "GENESIS",
            {"id": sid, "ts": ts, "state": state},
        )
        self._snapshots[sid] = {
            "id": sid, "ts": ts, "state": copy.deepcopy(state),
            "integrity": snapshot_hash,
        }
        self._chain.append(snapshot_hash)
        return sid

    def restore(self, snapshot_id: str) -> dict:
        if snapshot_id not in self._snapshots:
            raise KeyError(f"snapshot '{snapshot_id}' não encontrado")
        return copy.deepcopy(self._snapshots[snapshot_id]["state"])

    def list(self) -> list[SnapshotMetadata]:
        return [
            SnapshotMetadata(
                s["id"], s["ts"], len(str(s["state"])), s.get("integrity", "")
            )
            for s in self._snapshots.values()
        ]

    def verify_integrity(self) -> bool:
        if len(self._snapshots) != len(self._chain):
            return False
        previous = "GENESIS"
        for snapshot in self._snapshots.values():
            expected = chain_hash(
                previous,
                {"id": snapshot["id"], "ts": snapshot["ts"], "state": snapshot["state"]},
            )
            if expected != snapshot.get("integrity"):
                return False
            previous = expected
        return True

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("snapshot", self.NAME, True,
                       snapshot_count=len(self._snapshots),
                       chain_integrity=self.verify_integrity())