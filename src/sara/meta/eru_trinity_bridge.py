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
    recovery_candidates: list[dict] = field(default_factory=list)


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
        candidates = self.advise_recovery(cycle_id=cycle_id)
        audit.recovery_candidates = candidates
        return {
            "ok": True,
            "cycle_id": cycle_id,
            "observations": [o.__dict__ for o in audit.observations],
            "drifts": drifts,
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
