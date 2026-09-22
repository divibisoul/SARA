"""SARA — Núcleo: SistemaVivo.
Status: IMPLEMENTED.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional
from sara.regeneration.regenerative_loop import RegenerativeLoop, LoopReport
from sara.monitoring.storm_monitor import StormMonitor
from sara.monitoring.decision_trace import DecisionTrace
from sara.contracts import ModuleRegistry
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.core.connected_runtime import ConnectedRuntime


@dataclass
class CycleResult:
    cycle_id: str
    input: str
    loop_report: LoopReport
    trace_hash: str
    monitoring_id: Optional[str] = None
    registry_snapshot: Optional[dict] = None
    provenance_summary: Optional[dict] = None


class SistemaVivo:
    NAME = "SistemaVivo"
    VERSION = "5.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.NUCLEAR
    DEPENDENCIES = ("RegenerativeLoop", "StormMonitor", "DecisionTrace", "ModuleRegistry", "ProvenanceTracker")
    CYCLE_PHASES = tuple(CyclePhase)

    def __init__(self, loop: RegenerativeLoop, monitor: StormMonitor,
                 trace: DecisionTrace, registry: ModuleRegistry | None = None,
                 provenance: Any = None,
                 connected_runtime: ConnectedRuntime | None = None) -> None:
        self._loop = loop
        self._monitor = monitor
        self._trace = trace
        self._registry = registry
        self._provenance = provenance
        self._connected_runtime = connected_runtime
        self._active_monitor: Optional[str] = None
        self._cycle_count = 0

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "connected_runtime": self._connected_runtime is not None,
        }

    def process(self, input_text, cycle_id=None, monitor_hours=0.0) -> CycleResult:
        self._cycle_count += 1
        if self._connected_runtime is not None:
            connection = self._connected_runtime.validate_connection()
            if not connection["ok"]:
                raise RuntimeError({
                    "message": "SistemaVivo bloqueado por invariantes de conexão",
                    "invariants": connection["invariants"],
                })
        cid = cycle_id or f"sv-cycle-{self._cycle_count}"
        start = self._trace.log({
            "event": "cycle_start", "cycle_id": cid,
            "input_len": len(str(input_text)),
        })
        report = self._loop.run(input_text, cycle_id=cid)

        monitoring_id = None
        if monitor_hours > 0:
            monitoring_id = self._monitor.start(cid, monitor_hours)
            self._active_monitor = monitoring_id

        self._trace.log({
            "event": "cycle_end", "cycle_id": cid,
            "converged": report.converged,
            "rollback": report.rollback_performed,
            "evidence_hash": report.execution_report.get("evidence_hash"),
        })
        snap = self._registry.snapshot() if self._registry else None
        prov_summary = self._provenance.report() if self._provenance else None
        return CycleResult(cid, input_text, report, start.hash, monitoring_id, snap, prov_summary)

    def state(self) -> dict:
        return {
            "cycles_executed": self._cycle_count,
            "loop_history": len(self._loop.history()),
            "active_monitor": self._active_monitor,
            "trace_valid": self._trace.verify(),
            "registry_snapshot": self._registry.snapshot() if self._registry else None,
            "provenance": self._provenance.report() if self._provenance else None,
            "connected_runtime": (
                self._connected_runtime.validate_connection()
                if self._connected_runtime is not None else None
            ),
        }

    def reset(self) -> None:
        self._active_monitor = None
