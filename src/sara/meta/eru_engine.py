"""SARA — Meta: ERU_Engine v2.
Status: IMPLEMENTED (deep).
"""
from __future__ import annotations
import copy
import re
from dataclasses import dataclass, field
from typing import Any
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.hashing import hash_json
from sara.infra.clock import now_iso
from sara.core.provenance import Provenance


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

    def __init__(self, provenance=None, temporal=None) -> None:
        self._snapshots: dict[str, FrozenState] = {}
        self._provenance = provenance
        self._temporal = temporal

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
        previous = self._snapshots[name].hash if name in self._snapshots else None
        if previous is not None and previous == h:
            return h
        self._snapshots[name] = FrozenState(
            name=name, state=copy.deepcopy(state), hash=h, ts=now_iso()
        )
        if self._temporal is not None:
            self._temporal.insert({
                "event": "eru_freeze",
                "name": name,
                "state_hash": h,
                "previous_hash": previous,
                "ts": now_iso(),
            })
        if self._provenance is not None:
            self._provenance.register(
                f"ERU.freeze.{name}",
                Provenance.RECONSTRUCTED,
                "Estado congelado durante ciclo SARA",
                source="ERU_Engine.freeze",
            )
        return h

    def _walk_keys(self, obj: Any, prefix: str = "") -> dict[str, Any]:
        out: dict[str, Any] = {}
        if isinstance(obj, dict):
            for k, v in obj.items():
                path = f"{prefix}.{k}" if prefix else str(k)
                if isinstance(v, (dict, list)):
                    out.update(self._walk_keys(v, path))
                else:
                    out[path] = v
        elif isinstance(obj, list):
            for index, value in enumerate(obj):
                path = f"{prefix}[{index}]"
                if isinstance(value, (dict, list)):
                    out.update(self._walk_keys(value, path))
                else:
                    out[path] = value
        else:
            out[prefix or "$"] = obj
        return out

    def snapshot(self, name: str) -> FrozenState | None:
        """Retorna cópia isolada do snapshot congelado, sem expor estado interno mutável."""
        frozen = self._snapshots.get(name)
        return copy.deepcopy(frozen) if frozen is not None else None

    def verify_snapshot(self, name: str) -> bool:
        """Verifica a integridade criptográfica de um snapshot ERU existente."""
        frozen = self._snapshots.get(name)
        if frozen is None:
            return False
        return hash_json(frozen.state) == frozen.hash

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
            found, value = self._lookup_path(old_state, path)
            if found:
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
    def _lookup_path(obj: Any, path: str) -> tuple[bool, Any]:
        tokens = re.findall(r"([^.\[\]]+)|\[(\d+)\]", path)
        cur = obj
        for key, index in tokens:
            if index:
                if not isinstance(cur, list):
                    return False, None
                idx = int(index)
                if idx >= len(cur):
                    return False, None
                cur = cur[idx]
            else:
                if not isinstance(cur, dict) or key not in cur:
                    return False, None
                cur = cur[key]
        return True, cur

    @staticmethod
    def _get_path(obj: Any, path: str) -> Any:
        tokens = re.findall(r"([^.\[\]]+)|\[(\d+)\]", path)
        cur = obj
        for key, index in tokens:
            if index:
                if not isinstance(cur, list):
                    return None
                idx = int(index)
                if idx >= len(cur):
                    return None
                cur = cur[idx]
            else:
                if not isinstance(cur, dict) or key not in cur:
                    return None
                cur = cur[key]
        return cur

    @staticmethod
    def _set_path(obj: Any, path: str, value: Any) -> None:
        tokens = re.findall(r"([^.\[\]]+)|\[(\d+)\]", path)
        if not tokens:
            return
        cur = obj
        for pos, (key, index) in enumerate(tokens):
            last = pos == len(tokens) - 1
            if index:
                if not isinstance(cur, list):
                    return
                idx = int(index)
                while len(cur) <= idx:
                    cur.append({})
                if last:
                    cur[idx] = copy.deepcopy(value)
                    return
                cur = cur[idx]
                continue
            if not isinstance(cur, dict):
                return
            if last:
                cur[key] = copy.deepcopy(value)
                return
            next_is_list = bool(tokens[pos + 1][1])
            if key not in cur or not isinstance(cur[key], (dict, list)):
                cur[key] = [] if next_is_list else {}
            cur = cur[key]

    def audit(self, reference: str, target: str) -> AuditReport:
        if reference not in self._snapshots or target not in self._snapshots:
            return AuditReport(
                before_hash=self._snapshots[reference].hash if reference in self._snapshots else "",
                after_hash=self._snapshots[target].hash if target in self._snapshots else "",
                diff=DiffReport(lost=["__missing_snapshot__"]),
                recovered_paths=[],
                final_state=None,
            )
        diff = self.compare(reference, target)
        rec = self.recover(reference, target)
        return AuditReport(
            before_hash=self._snapshots[reference].hash,
            after_hash=self._snapshots[target].hash,
            diff=diff,
            recovered_paths=rec["recovered_paths"],
            final_state=rec["state_fused"],
        )

    def checkpoint(self, cycle_id: str, iteration: int, state: Any) -> dict:
        """Cria checkpoint identificável e imutável para rollback/reconstrução."""
        if not cycle_id or iteration < 1:
            raise ValueError("cycle_id e iteration válidos são obrigatórios")
        name = f"{cycle_id}:checkpoint:{iteration}"
        state_hash = self.freeze(name, {
            "cycle_id": cycle_id,
            "iteration": int(iteration),
            "state": copy.deepcopy(state),
        })
        return {
            "name": name,
            "cycle_id": cycle_id,
            "iteration": int(iteration),
            "state_hash": state_hash,
            "verified": self.verify_snapshot(name),
        }

    def detect_information_loss(self, older: str, newer: str) -> dict:
        """Detecta perda e informa quando a reconstrução é ou não demonstrável."""
        diff = self.compare(older, newer)
        if "__missing_snapshot__" in diff.lost:
            return {
                "reconstructable": False,
                "reason": "missing_snapshot",
                "lost_paths": list(diff.lost),
            }
        recoverable: list[str] = []
        irrecoverable: list[str] = []
        old_state = self._snapshots[older].state
        for path in diff.lost:
            found, _ = self._lookup_path(old_state, path)
            if found:
                recoverable.append(path)
            else:
                irrecoverable.append(path)
        return {
            "reconstructable": not irrecoverable,
            "reason": "ok" if not irrecoverable else "missing_evidence_for_lost_paths",
            "lost_paths": list(diff.lost),
            "recoverable_paths": recoverable,
            "irrecoverable_paths": irrecoverable,
        }

    def reconstructability(self, older: str, newer: str) -> dict:
        """Retorna uma decisão explícita sobre a reversibilidade disponível."""
        if not self.verify_snapshot(older) or not self.verify_snapshot(newer):
            return {
                "status": "UNMEASURABLE",
                "reason": "snapshot_integrity_unverified",
            }
        loss = self.detect_information_loss(older, newer)
        return {
            "status": "REAL" if loss["reconstructable"] else "UNMEASURABLE",
            **loss,
        }

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("persistence", self.NAME, True,
                       snapshots=len(self._snapshots))