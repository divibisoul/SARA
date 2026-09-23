"""SARA — Meta: ERU_Engine v2.
Status: IMPLEMENTED (deep).
"""
from __future__ import annotations
import copy
import re
import inspect
import hashlib
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
        self._behavior_observations: dict[str, list[dict[str, Any]]] = {}
        self._provenance = provenance
        self._temporal = temporal

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "snapshots": len(self._snapshots),
            "behavior_observations": sum(len(v) for v in self._behavior_observations.values()),
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

    def checkpoint(
        self,
        name: str,
        state: Any,
        *,
        cycle_id: str,
        phase: str,
        source: str = "ERU_Engine.checkpoint",
    ) -> dict[str, Any]:
        """Cria checkpoint verificável sem alegar reversibilidade inexistente."""
        if not name or not cycle_id or not phase:
            raise ValueError("ERU_CHECKPOINT_FIELDS_REQUIRED")
        snapshot_name = f"CHECKPOINT::{cycle_id}::{phase}::{name}"
        state_hash = self.freeze(snapshot_name, state)
        record = {
            "name": snapshot_name,
            "logical_name": name,
            "snapshot_name": snapshot_name,
            "cycle_id": cycle_id,
            "phase": phase,
            "hash": state_hash,
            "source": source,
            "status": "REAL",
            "verified": self.verify_snapshot(snapshot_name),
            "reversible": self.has_snapshot(snapshot_name),
        }
        if self._temporal is not None:
            self._temporal.insert({
                "event": "eru_checkpoint",
                **record,
                "ts": now_iso(),
            })
        if self._provenance is not None:
            self._provenance.register(
                f"ERU.checkpoint.{cycle_id}.{phase}.{name}",
                Provenance.RECONSTRUCTED,
                "Checkpoint explícito do estado do ciclo",
                source=source,
            )
        return copy.deepcopy(record)

    def detect_information_loss(self, older: str, newer: str) -> dict[str, Any]:
        """Detecta perda estrutural entre snapshots; ausência de snapshot é inconclusiva."""
        diff = self.compare(older, newer)
        if diff.lost == ["__missing_snapshot__"]:
            return {
                "status": "UNMEASURABLE",
                "loss_detected": False,
                "lost_paths": [],
                "recoverable": [],
                "reason": "missing_snapshot",
                "older": older,
                "newer": newer,
            }
        recovery = self.recover(older, newer)
        recoverable = list(recovery.get("recovered_paths", []))
        return {
            "status": "REAL",
            "loss_detected": bool(diff.lost),
            "lost_paths": list(diff.lost),
            "recoverable": recoverable,
            "changed_paths": list(diff.changed),
            "added_paths": list(diff.added),
            "older": older,
            "newer": newer,
        }

    def reconstructability(self, older: str, newer: str) -> dict[str, Any]:
        """Determina se a perda estrutural pode ser reconstruída pelos snapshots."""
        if older not in self._snapshots or newer not in self._snapshots:
            return {
                "status": "UNMEASURABLE",
                "reconstructable": False,
                "reconstructible": False,
                "reason": "missing_snapshot",
                "older": older,
                "newer": newer,
            }
        diff = self.compare(older, newer)
        recovery = self.recover(older, newer)
        lost = set(diff.lost)
        recovered = set(recovery.get("recovered_paths", []))
        reconstructible = lost.issubset(recovered)
        return {
            "status": "REAL",
            "reconstructable": reconstructible,
            "reconstructible": reconstructible,
            "lost_paths": sorted(lost),
            "recovered_paths": sorted(recovered),
            "unrecovered_paths": sorted(lost - recovered),
            "evidence": "snapshot_pair_and_structural_recovery",
            "older": older,
            "newer": newer,
        }

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

    @staticmethod
    def _callable_source_hash(member: Any) -> str | None:
        try:
            source = inspect.getsource(member)
        except (OSError, TypeError):
            return None
        return hashlib.sha256(source.encode("utf-8")).hexdigest()

    def freeze_capabilities(self, name: str, module: Any) -> str:
        """Congela capacidades observáveis de um módulo.

        Inclui contrato declarado, métodos públicos, assinaturas e, quando
        disponível, impressão digital do código-fonte do método. Isso amplia
        o ERU além do simples diff de dados sem afirmar equivalência funcional.
        """
        if not name:
            raise ValueError("name é obrigatório")

        describe = {}
        describe_fn = getattr(module, "describe", None)
        if callable(describe_fn):
            described = describe_fn()
            if isinstance(described, dict):
                describe = copy.deepcopy(described)

        methods: dict[str, dict[str, Any]] = {}
        for attr_name, member in inspect.getmembers(module, predicate=callable):
            if attr_name.startswith("_"):
                continue
            try:
                signature = str(inspect.signature(member))
            except (TypeError, ValueError):
                signature = "UNAVAILABLE"
            source_text = None
            try:
                source_text = inspect.getsource(member)
            except (OSError, TypeError):
                pass
            methods[attr_name] = {
                "signature": signature,
                "source_hash": (
                    hashlib.sha256(source_text.encode("utf-8")).hexdigest()
                    if source_text is not None else None
                ),
                "source_text": source_text,
                "source_available": source_text is not None,
            }

        state = {
            "kind": "capability_snapshot",
            "module_type": f"{type(module).__module__}.{type(module).__qualname__}",
            "describe": describe,
            "methods": methods,
        }
        snapshot_name = f"CAP::{name}"
        snapshot_hash = self.freeze(snapshot_name, state)
        return snapshot_hash

    def has_snapshot(self, name: str) -> bool:
        return name in self._snapshots

    def record_behavior_observation(
        self,
        snapshot_name: str,
        method: str,
        probe_id: str,
        input_digest: str,
        output_digest: str,
        *,
        success: bool,
        evidence_source: str = "external_execution",
    ) -> dict[str, Any]:
        """Registra evidência observada sem alegar equivalência funcional total.

        A ERU não executa métodos arbitrários. O chamador fornece o resultado
        efetivamente observado e seus digests. A evidência é vinculada ao
        snapshot CAP::* correspondente para permitir comparação posterior.
        """
        if snapshot_name not in self._snapshots:
            raise ValueError("ERU_BEHAVIOR_SNAPSHOT_MISSING")
        if not method or not probe_id or not input_digest or not output_digest:
            raise ValueError("ERU_BEHAVIOR_FIELDS_REQUIRED")
        observation = {
            "snapshot_name": snapshot_name,
            "method": method,
            "probe_id": probe_id,
            "input_digest": input_digest,
            "output_digest": output_digest,
            "success": bool(success),
            "evidence_source": evidence_source,
            "functional_equivalence_proven": False,
        }
        self._behavior_observations.setdefault(snapshot_name, []).append(copy.deepcopy(observation))
        if self._temporal is not None:
            self._temporal.insert({
                "event": "eru_behavior_observation",
                **observation,
                "ts": now_iso(),
            })
        if self._provenance is not None:
            self._provenance.register(
                f"ERU.behavior.{snapshot_name}.{method}.{probe_id}",
                Provenance.UNKNOWN,
                "Evidência comportamental observada; origem histórica da capacidade permanece não determinada",
                source="ERU_Engine.record_behavior_observation",
            )
        return copy.deepcopy(observation)

    def behavior_diff(self, older: str, newer: str) -> dict[str, Any]:
        """Compara comportamento apenas para probes observados em ambos snapshots."""
        if older not in self._snapshots or newer not in self._snapshots:
            return {"ok": False, "reason": "missing_snapshot"}
        old = {
            (o["method"], o["probe_id"], o["input_digest"]): o
            for o in self._behavior_observations.get(older, [])
        }
        new = {
            (o["method"], o["probe_id"], o["input_digest"]): o
            for o in self._behavior_observations.get(newer, [])
        }
        common = sorted(set(old) & set(new))
        matched = []
        changed = []
        for key in common:
            a, b = old[key], new[key]
            item = {
                "method": key[0],
                "probe_id": key[1],
                "input_digest": key[2],
                "older_output_digest": a["output_digest"],
                "newer_output_digest": b["output_digest"],
                "older_success": a["success"],
                "newer_success": b["success"],
            }
            if a["output_digest"] == b["output_digest"] and a["success"] == b["success"]:
                matched.append(item)
            else:
                changed.append(item)
        return {
            "ok": True,
            "older": older,
            "newer": newer,
            "matched_observations": matched,
            "changed_observations": changed,
            "older_only_observations": sorted(set(old) - set(new)),
            "newer_only_observations": sorted(set(new) - set(old)),
            "behavioral_evidence_available": bool(common),
            "behaviorally_equivalent_for_observed_probes": bool(common) and not changed,
            "functional_equivalence_proven": False,
            "proof_scope": "observed_probes_only",
        }

    def capability_diff(self, older: str, newer: str) -> dict[str, Any]:
        """Compara snapshots CAP::* por capacidade nominal/assinatura/código."""
        if older not in self._snapshots or newer not in self._snapshots:
            return {
                "ok": False,
                "reason": "missing_snapshot",
                "removed_methods": [],
                "added_methods": [],
                "changed_methods": [],
                "changed_contract": [],
            }

        old = self._snapshots[older].state
        new = self._snapshots[newer].state
        old_methods = old.get("methods", {}) if isinstance(old, dict) else {}
        new_methods = new.get("methods", {}) if isinstance(new, dict) else {}
        old_names = set(old_methods)
        new_names = set(new_methods)

        added_methods = sorted(new_names - old_names)
        removed_methods = sorted(old_names - new_names)
        changed_methods = sorted(
            name for name in old_names & new_names
            if old_methods[name] != new_methods[name]
        )

        old_desc = old.get("describe", {}) if isinstance(old, dict) else {}
        new_desc = new.get("describe", {}) if isinstance(new, dict) else {}
        contract_keys = (
            "status", "role", "dependencies", "phases",
            "version", "name",
        )
        changed_contract = sorted(
            key for key in contract_keys
            if old_desc.get(key) != new_desc.get(key)
        )

        recoverable_removed_methods = sorted(
            name for name in removed_methods
            if old_methods.get(name, {}).get("source_available") is True
            and bool(old_methods.get(name, {}).get("source_text"))
        )
        recoverable_changed_methods = sorted(
            name for name in changed_methods
            if old_methods.get(name, {}).get("source_available") is True
            and bool(old_methods.get(name, {}).get("source_text"))
        )
        return {
            "ok": True,
            "older": older,
            "newer": newer,
            "added_methods": added_methods,
            "removed_methods": removed_methods,
            "changed_methods": changed_methods,
            "changed_contract": changed_contract,
            "recoverable_removed_methods": recoverable_removed_methods,
            "recoverable_changed_methods": recoverable_changed_methods,
            "functional_equivalence_proven": False,
        }

    def audit_capabilities(self, older: str, newer: str) -> dict[str, Any]:
        diff = self.capability_diff(older, newer)
        if not diff.get("ok"):
            return diff
        structural = self.compare(older, newer)
        return {
            **diff,
            "structural_diff": {
                "lost": structural.lost,
                "added": structural.added,
                "changed": structural.changed,
                "kept": structural.kept,
            },
        }

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
            if value is not self._MISSING:
                self._set_path(new_state, path, value)
                recovered.append(path)
        return {
            "state_fused": new_state,
            "recovered_paths": recovered,
            "kept": diff.kept,
            "added": diff.added,
            "changed": diff.changed,
        }

    _MISSING = object()

    @classmethod
    def _get_path(cls, obj: Any, path: str) -> Any:
        tokens = re.findall(r"([^.\[\]]+)|\[(\d+)\]", path)
        cur = obj
        for key, index in tokens:
            if index:
                if not isinstance(cur, list):
                    return cls._MISSING
                idx = int(index)
                if idx >= len(cur):
                    return cls._MISSING
                cur = cur[idx]
            else:
                if not isinstance(cur, dict) or key not in cur:
                    return cls._MISSING
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