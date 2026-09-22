from __future__ import annotations
import uuid
from typing import Any

from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.omega.models import ETRContext, OmegaCycleReport
from sara.omega.scanner import SystemMetricsScanner
from sara.omega.nuclei import ETRGenesisSuite
from sara.omega.soul_services import HabitLearningEngine, AnticipationEngine, MicroMacroManager
from sara.omega.hal import GenericHostAdapter
from sara.omega.security import CodeValidator, PermissionManager, AuditLog
from sara.security.safe_sandbox import SafeSandbox


class SoulETROmegaSystem:
    NAME = "SoulETROmegaSystem"
    VERSION = "1.1"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = ("ARA_Extended", "ETR_Extended", "ITR_Extended", "ERU_Engine")
    CYCLE_PHASES = (
        CyclePhase.INGESTION, CyclePhase.AUDIT, CyclePhase.STRATEGY,
        CyclePhase.EXECUTION, CyclePhase.VALIDATION, CyclePhase.MONITORING,
    )

    def __init__(self, *, safe_sandbox: SafeSandbox | None = None) -> None:
        self.scanner = SystemMetricsScanner()
        self.adapter = GenericHostAdapter(self.scanner)
        self.etr = ETRGenesisSuite()
        self.habits = HabitLearningEngine()
        self.anticipation = AnticipationEngine()
        self.micro_macro = MicroMacroManager()
        self.code_validator = CodeValidator(safe_sandbox or SafeSandbox())
        self.permissions = PermissionManager()
        self.audit_log = AuditLog()
        self._last: OmegaCycleReport | None = None

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "execution": "real_host_metrics_only",
            "android_privileged_operations": "external_adapter_required",
            "device_specific": False,
            "hal": self.adapter.capabilities().__dict__,
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
        state = self.micro_macro.transition(health_score=health, completed=self.micro_macro.completed + 1)
        arm = self.etr.adaptive.choose()
        adaptation = self.etr.adaptive.update(arm, reward=(0.5 if success else -0.5))
        self.audit_log.append("omega_cycle", cycle_id=cycle_id, ok=success, health_score=health)
        report = OmegaCycleReport(
            cycle_id=cycle_id, ok=success,
            analysis=reports, plan=plan,
            results=tuple(self._result_objects(results)),
            adaptation={**adaptation, "phase_state": state},
            evidence={
                "metrics": [m.__dict__ for m in metrics],
                "health_score": health,
                "scanner": self.scanner.NAME,
                "permissions": [p.__dict__ for p in self.permissions.inspect()],
            },
        )
        self._last = report
        return report

    def validate_code(self, code: str) -> dict[str, Any]:
        result = self.code_validator.validate(code)
        self.audit_log.append("code_validation", approved=result["approved"], nodes=result["nodes"])
        return result

    @staticmethod
    def _result_objects(results):
        from sara.omega.models import ETRResult
        return tuple(ETRResult(
            action_id=r["action_id"], ok=r["ok"], output=r.get("output", {}),
            rolled_back=bool(r.get("rollback")), rollback_output=r.get("rollback", {}),
        ) for r in results)

    @staticmethod
    def _health(metrics) -> float:
        scores = [
            1.0 - max(0.0, min(100.0, m.value)) / 100.0
            for m in metrics
            if m.name in {"cpu_utilization", "memory_utilization", "disk_utilization"}
        ]
        return sum(scores) / len(scores) if scores else 0.0

    def last_report(self) -> OmegaCycleReport | None:
        return self._last
