"""SARA — Core: unified ERU + ARA/ETR/ITR orchestration.
Status: IMPLEMENTED — integração aditiva sobre TrinitySynergy.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.core.ara_extended import ARA_Extended
from sara.core.etr_extended import ETR_Extended
from sara.core.itr_extended import ITR_Extended
from sara.core.trinity_synergy import TrinitySynergy, TrinityReport
from sara.meta.eru_engine import ERU_Engine
from sara.meta.eru_trinity_bridge import ERUTrinityBridge


@dataclass
class UnifiedERUReport:
    trinity_report: TrinityReport
    cycle_audits: list[dict] = field(default_factory=list)
    recovery_candidates: list[dict] = field(default_factory=list)


class TrinityERUUnified:
    """Adiciona ERU à Trindade sem eliminar TrinitySynergy."""

    NAME = "TrinityERUUnified"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = (
        "ARA_Extended", "ETR_Extended", "ITR_Extended",
        "ERU_Engine", "ERUTrinityBridge",
    )
    CYCLE_PHASES = (
        CyclePhase.AUDIT, CyclePhase.SNAPSHOT, CyclePhase.REGENERATION,
        CyclePhase.ETHICS, CyclePhase.STRATEGY, CyclePhase.EXECUTION,
        CyclePhase.VALIDATION, CyclePhase.PERSISTENCE,
    )

    def __init__(
        self,
        ara: ARA_Extended,
        etr: ETR_Extended,
        itr: ITR_Extended,
        eru: ERU_Engine,
        bridge: ERUTrinityBridge | None = None,
        max_iterations: int = 3,
    ) -> None:
        self._ara = ara
        self._etr = etr
        self._itr = itr
        self._eru = eru
        self._bridge = bridge or ERUTrinityBridge(eru)
        self._bridge.register_trinity(ara, etr, itr)
        self._trinity = TrinitySynergy(
            ara, etr, itr, max_iterations=max_iterations, eru=eru
        )
        self._trinity._eru_bridge = self._bridge

    def describe(self) -> dict:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "bridge": self._bridge.describe(),
            "trinity": self._trinity.describe(),
        }

    def assess(self, target: str) -> dict:
        return self._trinity.assess(target)

    def apply_to(self, target: str) -> UnifiedERUReport:
        report = self._trinity.apply_to(target)
        audits: list[dict] = []
        candidates: list[dict] = []
        for cycle_id in self._bridge.observed_cycle_ids():
            audit = self._bridge.audit_cycle(cycle_id)
            audits.append(audit)
            candidates.extend(audit.get("recovery_candidates", []))
        return UnifiedERUReport(
            trinity_report=report,
            cycle_audits=audits,
            recovery_candidates=candidates,
        )

    def audit_cycle(self, cycle_id: str) -> dict:
        return self._bridge.audit_cycle(cycle_id)

    def recovery_advice(self, cycle_id: str) -> list[dict]:
        return self._bridge.advise_recovery(cycle_id=cycle_id)

    def bridge(self) -> ERUTrinityBridge:
        return self._bridge

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record(
                "persistence",
                self.NAME,
                True,
                bridge=self._bridge.describe(),
            )
