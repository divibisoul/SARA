"""SARA — Meta: ERU_Engine v2.
Status: IMPLEMENTED (deep).
"""
from __future__ import annotations
import copy
from dataclasses import dataclass, field
from typing import Any
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.hashing import hash_json
from sara.infra.clock import now_iso


@dataclass
class FrozenState:
    name: str
    state: Any
    hash: str
    ts: str


@dataclass
class DiffReport:
    lost: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)


@dataclass
class AuditReport:
    before_hash: str
    after_hash: str
    diff: DiffReport
    recovered_paths: list[str]
    final_state: Any


class ERU_Engine:
    NAME = "ERU_Engine"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = ("ProvenanceTracker", "TemporalVectorDB")
    CYCLE_PHASES = (CyclePhase.PERSISTENCE,)

    def __init__(self) -> None:
        self._snapshots: dict[str, FrozenState] = {}

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "snapshots": len(self._snapshots),
        }

    def freeze(self, name: str, state: Any) -> str:
        h = hash_json(state)
        self._snapshots[name] = FrozenState(name=name, state=copy.deepcopy(state),
                                             hash=h, ts=now_iso())
        return h

    def _walk_keys(self, obj: Any, prefix: str = "") -> dict[str, Any]:
        out: dict[str, Any] = {}
        if isinstance(obj, dict):
            for k, v in obj.items():
                path = f"{prefix}.{k}" if prefix else str(k)
                if isinstance(v, dict):
                    out.update(self._walk_keys(v, path))
                else:
                    out[path] = v
        return out

    def compare(self, older: str, newer: str) -> DiffReport:
        if older not in self._snapshots or newer not in self._snapshots:
            return DiffReport(lost=["__missing_snapshot__"])
        old_flat = self._walk_keys(self._snapshots[older].state)
        new_flat = self._walk_keys(self._snapshots[newer].state)
        old_keys = set(old_flat.keys())
        new_keys = set(new_flat.keys())
        changed = [k for k in old_keys & new_keys if old_flat[k] != new_flat[k]]
        return DiffReport(
            lost=sorted(old_keys - new_keys),
            added=sorted(new_keys - old_keys),
            kept=sorted(old_keys & new_keys - set(changed)),
            changed=sorted(changed),
        )

    def recover(self, older: str, newer: str) -> dict:
        diff = self.compare(older, newer)
        old_state = self._snapshots[older].state
        new_state = copy.deepcopy(self._snapshots[newer].state)
        recovered: list[str] = []
        for path in diff.lost:
            value = self._get_path(old_state, path)
            if value is not None:
                self._set_path(new_state, path, value)
                recovered.append(path)
        return {
            "state_fused": new_state,
            "recovered_paths": recovered,
            "kept": diff.kept,
            "added": diff.added,
            "changed": diff.changed,
        }

    @staticmethod
    def _get_path(obj: Any, path: str) -> Any:
        parts = path.split(".")
        cur = obj
        for p in parts:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                return None
        return cur

    @staticmethod
    def _set_path(obj: Any, path: str, value: Any) -> None:
        parts = path.split(".")
        cur = obj
        for p in parts[:-1]:
            if p not in cur or not isinstance(cur[p], dict):
                cur[p] = {}
            cur = cur[p]
        cur[parts[-1]] = value

    def audit(self, reference: str, target: str) -> AuditReport:
        diff = self.compare(reference, target)
        rec = self.recover(reference, target)
        return AuditReport(
            before_hash=self._snapshots[reference].hash,
            after_hash=self._snapshots[target].hash,
            diff=diff,
            recovered_paths=rec["recovered_paths"],
            final_state=rec["state_fused"],
        )

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("persistence", self.NAME, True,
                       snapshots=len(self._snapshots))