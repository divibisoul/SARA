from __future__ import annotations
import uuid
from dataclasses import dataclass
from typing import Any

from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.omega.models import ETRContext, OmegaCycleReport
from sara.omega.scanner import SystemMetricsScanner
from sara.omega.nuclei import ETRGenesisSuite
from sara.omega.soul_services import HabitLearningEngine, AnticipationEngine, MicroMacroManager


class SoulETROmegaSystem:
    """Orquestrador Omega adaptado ao SARA, sem substituir o ciclo regenerativo.

    A execução é explícita: chamar run_cycle() produz evidência real e não
    declara sucesso apenas por estar configurado.
    """
    NAME = "SoulETROmegaSystem"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = ("ARA_Extended", "ETR_Extended", "ITR_Extended", "ERU_Engine")
    CYCLE_PHASES = (
        CyclePhase.INGESTION, CyclePhase.AUDIT, CyclePhase.STRATEGY,
        CyclePhase.EXECUTION, CyclePhase.VALIDATION, CyclePhase.MONITORING,
    )

    def __init__(self) -> None:
        self.scanner = SystemMetricsScanner()
        self.etr = ETRGenesisSuite()
        self.habits = HabitLearningEngine()
        self.anticipation = AnticipationEngine()
        self.micro_macro = MicroMacroManager()
        self._last: OmegaCycleReport | None = None

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "execution": "real_host_metrics_only",
            "android_privileged_operations": "not_assumed",
            "device_specific": False,
        }

    def run_cycle(self, facts: dict[str, Any] | None = None) -> OmegaCycleReport:
        cycle_id = f"omega-{uuid.uuid4().hex[:12]}"
        metrics = self.scanner.scan()
        context = ETRContext(cycle_id, metrics, dict(facts or {}))
        reports = self.etr.analyze(context)
        reality = next((r for r in reports if r.nucleus == "ETR_RealityFilterNucleus"), None)
        if reality is not None and not reality.ok:
            raise RuntimeError("OMEGA_REALITY_FILTER_REJECTED")
        plan = self.etr.build_plan(context, reports)
        results = self.etr.execute(plan)
        success = all(r.get("ok", False) for r in results) if results else True
        health = self._health(metrics)
        state = self.micro_macro.transition(health_score=health, completed=(self.micro_macro.completed + 1))
        adaptation = self.etr.adaptive.update(
            self.etr.adaptive.choose(),
            reward=(0.5 if success else -0.5),
        )
        report = OmegaCycleReport(
            cycle_id=cycle_id, ok=success,
            analysis=reports, plan=plan,
            results=tuple(self._result_objects(results)),
            adaptation={**adaptation, "phase_state": state},
            evidence={
                "metrics": [m.__dict__ for m in metrics],
                "health_score": health,
                "scanner": self.scanner.NAME,
            },
        )
        self._last = report
        return report

    @staticmethod
    def _result_objects(results):
        from sara.omega.models import ETRResult
        return tuple(
            ETRResult(
                action_id=r["action_id"],
                ok=r["ok"],
                output=r.get("output", {}),
                rolled_back=bool(r.get("rollback")),
                rollback_output=r.get("rollback", {}),
            )
            for r in results
        )

    @staticmethod
    def _health(metrics) -> float:
        scores = []
        for m in metrics:
            if m.name in {"cpu_utilization", "memory_utilization", "disk_utilization"}:
                scores.append(1.0 - max(0.0, min(100.0, m.value)) / 100.0)
        return sum(scores) / len(scores) if scores else 0.0

    def last_report(self) -> OmegaCycleReport | None:
        return self._last
