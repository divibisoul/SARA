"""SARA — Meta: ERU ↔ Trindade bridge.
Status: IMPLEMENTED — observação histórica e aconselhamento, sem recuperação automática.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.meta.eru_engine import ERU_Engine
from sara.meta.eru_drift_detector import ERUDriftDetector
from sara.meta.eru_recovery_advisor import ERURecoveryAdvisor


@dataclass(frozen=True)
class Observation:
    cycle_id: str
    phase: str
    snapshot_name: str
    snapshot_hash: str


@dataclass
class BridgeAudit:
    cycle_id: str
    observations: list[Observation] = field(default_factory=list)
    drifts: list[dict] = field(default_factory=list)
    capability_observations: list[dict] = field(default_factory=list)
    capability_drifts: list[dict] = field(default_factory=list)
    recovery_candidates: list[dict] = field(default_factory=list)
    capability_recovery_candidates: list[dict] = field(default_factory=list)
    behavioral_evidence: list[dict] = field(default_factory=list)
    behavioral_drifts: list[dict] = field(default_factory=list)


class ERUTrinityBridge:
    """Conecta a memória histórica da ERU ao ciclo ARA/ETR/ITR.

    A ponte observa e aconselha. Ela não altera automaticamente os módulos
    nem promove uma capacidade histórica sem evidência adicional.
    """

    NAME = "ERUTrinityBridge"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = ("ERU_Engine", "ARA_Extended", "ETR_Extended", "ITR_Extended")
    CYCLE_PHASES = (CyclePhase.SNAPSHOT, CyclePhase.PERSISTENCE)

    def __init__(self, eru: ERU_Engine) -> None:
        self._eru = eru
        self._drift = ERUDriftDetector(eru)
        self._advisor = ERURecoveryAdvisor(eru)
        self._trinity: dict[str, Any] = {}
        self._cycles: dict[str, BridgeAudit] = {}

    def describe(self) -> dict:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "registered_members": list(self._trinity),
            "observed_cycles": len(self._cycles),
        }

    def register_trinity(self, ara: Any, etr: Any, itr: Any) -> dict:
        self._trinity = {"ARA": ara, "ETR": etr, "ITR": itr}
        return {"registered": list(self._trinity)}

    def observe(self, cycle_id: str, phase: str, state: Any) -> Observation:
        if not cycle_id:
            raise ValueError("cycle_id é obrigatório")
        if not phase:
            raise ValueError("phase é obrigatória")
        snapshot_name = f"ERU:{cycle_id}:{phase}"
        snapshot_hash = self._eru.freeze(snapshot_name, state)
        observation = Observation(
            cycle_id=cycle_id,
            phase=phase,
            snapshot_name=snapshot_name,
            snapshot_hash=snapshot_hash,
        )
        audit = self._cycles.setdefault(cycle_id, BridgeAudit(cycle_id))
        audit.observations.append(observation)
        return observation

    def observed_cycle_ids(self) -> list[str]:
        return list(self._cycles)

    def observe_capabilities(self, cycle_id: str, phase: str) -> list[dict]:
        """Congela capacidades públicas de ARA/ETR/ITR nesta fase."""
        audit = self._cycles.setdefault(cycle_id, BridgeAudit(cycle_id))
        records: list[dict] = []
        for role, module in self._trinity.items():
            snapshot_name = f"{cycle_id}:{phase}:{role}"
            snapshot_hash = self._eru.freeze_capabilities(snapshot_name, module)
            record = {
                "cycle_id": cycle_id,
                "phase": phase,
                "role": role,
                "snapshot_name": f"CAP::{snapshot_name}",
                "snapshot_hash": snapshot_hash,
            }
            audit.capability_observations.append(record)
            records.append(record)
        return records

    @staticmethod
    def _capability_pairs(audit: BridgeAudit) -> dict[str, list[dict]]:
        by_role: dict[str, list[dict]] = {}
        for item in audit.capability_observations:
            by_role.setdefault(item["role"], []).append(item)
        return by_role

    def record_behavior(
        self,
        cycle_id: str,
        phase: str,
        role: str,
        method: str,
        probe_id: str,
        input_digest: str,
        output_digest: str,
        *,
        success: bool,
        evidence_source: str = "external_execution",
    ) -> dict:
        """Anexa observação comportamental à capacidade observada nesta fase."""
        audit = self._cycles.setdefault(cycle_id, BridgeAudit(cycle_id))
        snapshot_name = f"CAP::{cycle_id}:{phase}:{role}"
        if snapshot_name not in self._eru._snapshots:
            raise ValueError("ERU_BEHAVIOR_CAPABILITY_SNAPSHOT_MISSING")
        evidence = self._eru.record_behavior_observation(
            snapshot_name,
            method,
            probe_id,
            input_digest,
            output_digest,
            success=success,
            evidence_source=evidence_source,
        )
        audit.behavioral_evidence.append(evidence)
        return evidence

    def detect_behavioral_drift(self, cycle_id: str) -> list[dict]:
        audit = self._cycles.get(cycle_id)
        if audit is None:
            return []
        by_role: dict[str, list[dict]] = {}
        for item in audit.capability_observations:
            by_role.setdefault(item["role"], []).append(item)
        drifts: list[dict] = []
        for role, observations in by_role.items():
            for older, newer in zip(observations, observations[1:]):
                result = self._eru.behavior_diff(
                    older["snapshot_name"],
                    newer["snapshot_name"],
                )
                result["role"] = role
                result["from_phase"] = older["phase"]
                result["to_phase"] = newer["phase"]
                drifts.append(result)
        audit.behavioral_drifts = drifts
        return list(drifts)

    def detect_capability_drift(self, cycle_id: str) -> list[dict]:
        audit = self._cycles.get(cycle_id)
        if audit is None:
            return []

        by_role: dict[str, list[dict]] = {}
        for item in audit.capability_observations:
            by_role.setdefault(item["role"], []).append(item)

        drifts: list[dict] = []
        for role, observations in by_role.items():
            for older, newer in zip(observations, observations[1:]):
                result = self._eru.capability_diff(
                    older["snapshot_name"],
                    newer["snapshot_name"],
                )
                result["role"] = role
                result["from_phase"] = older["phase"]
                result["to_phase"] = newer["phase"]
                drifts.append(result)

        audit.capability_drifts = drifts
        return list(drifts)

    def detect_drift(self, cycle_id: str) -> list[dict]:
        audit = self._cycles.get(cycle_id)
        if audit is None:
            return []
        reports: list[dict] = []
        for older, newer in zip(audit.observations, audit.observations[1:]):
            result = self._drift.compute_drift(
                older.snapshot_name, newer.snapshot_name
            )
            result["from_phase"] = older.phase
            result["to_phase"] = newer.phase
            reports.append(result)
        audit.drifts = reports
        return list(reports)

    def advise_recovery(
        self,
        target: str | tuple[str, str] | None = None,
        cycle_id: str | None = None,
    ) -> list[dict]:
        if target is None:
            audit = self._cycles.get(cycle_id or "")
            if audit is None or len(audit.observations) < 2:
                return []
            older = audit.observations[-2].snapshot_name
            newer = audit.observations[-1].snapshot_name
        elif isinstance(target, tuple):
            older, newer = target
        else:
            raise ValueError("target deve ser (older, newer) quando fornecido")
        candidates = self._advisor.find_lost_capabilities(older, newer)
        return self._advisor.rank_by_impact(candidates)

    def align_trinity(self) -> dict:
        return {
            "ara_present": "ARA" in self._trinity,
            "etr_present": "ETR" in self._trinity,
            "itr_present": "ITR" in self._trinity,
            "eru_present": True,
            "alignment_ready": len(self._trinity) == 3,
        }

    def audit_cycle(self, cycle_id: str) -> dict:
        audit = self._cycles.get(cycle_id)
        if audit is None:
            return {"ok": False, "reason": "cycle_not_observed"}
        drifts = self.detect_drift(cycle_id)
        capability_drifts = self.detect_capability_drift(cycle_id)
        behavioral_drifts = self.detect_behavioral_drift(cycle_id)
        candidates = self.advise_recovery(cycle_id=cycle_id)
        audit.recovery_candidates = candidates

        capability_candidates: list[dict] = []
        for role, observations in self._capability_pairs(audit).items():
            for older, newer in zip(observations, observations[1:]):
                capability_candidates.extend(
                    self._advisor.find_lost_capabilities(
                        older["snapshot_name"], newer["snapshot_name"]
                    )
                )
        audit.capability_recovery_candidates = [
            c for c in capability_candidates
            if c.get("provenance") == "ERU_CAPABILITY_CANDIDATE"
        ]

        return {
            "ok": True,
            "cycle_id": cycle_id,
            "observations": [o.__dict__ for o in audit.observations],
            "drifts": drifts,
            "capability_drifts": capability_drifts,
            "capability_observations": list(audit.capability_observations),
            "capability_recovery_candidates": list(audit.capability_recovery_candidates),
            "behavioral_evidence": list(audit.behavioral_evidence),
            "behavioral_drifts": behavioral_drifts,
            "recovery_candidates": candidates,
            "alignment": self.align_trinity(),
        }

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record(
                "persistence",
                self.NAME,
                True,
                registered_members=list(self._trinity),
                observed_cycles=len(self._cycles),
            )
