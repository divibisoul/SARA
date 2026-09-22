"""SARA — Núcleo: SistemaVivo v4.
Status: IMPLEMENTED.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional
from sara.regeneration.regenerative_loop import RegenerativeLoop, LoopReport
from sara.monitoring.storm_monitor import StormMonitor
from sara.monitoring.decision_trace import DecisionTrace
from sara.contracts import ModuleRegistry


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
    VERSION = "4.0"

    def __init__(
        self,
        loop: RegenerativeLoop,
        monitor: StormMonitor,
        trace: DecisionTrace,
        registry: ModuleRegistry | None = None,
        provenance: Any = None,
    ) -> None:
        self._loop = loop
        self._monitor = monitor
        self._trace = trace
        self._registry = registry
        self._provenance = provenance
        self._active_monitor: Optional[str] = None
        self._cycle_count = 0

    def describe(self) -> dict:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "registry_attached": self._registry is not None,
            "provenance_attached": self._provenance is not None,
        }

    def process(self, input_text, cycle_id=None, monitor_hours=0.0) -> CycleResult:
        self._cycle_count += 1
        cid = cycle_id or f"sv-cycle-{self._cycle_count}"

        start_entry = self._trace.log({
            "event": "cycle_start",
            "cycle_id": cid,
            "input_len": len(str(input_text)),
        })
        report = self._loop.run(input_text, cycle_id=cid)

        monitoring_id = None
        if monitor_hours > 0:
            monitoring_id = self._monitor.start(cid, monitor_hours)
            self._active_monitor = monitoring_id

        self._trace.log({
            "event": "cycle_end",
            "cycle_id": cid,
            "converged": report.converged,
            "rollback": report.rollback_performed,
        })

        snap = self._registry.snapshot() if self._registry else None
        prov_summary = None
        if self._provenance is not None:
            try:
                prov_summary = self._provenance.report()
            except Exception:
                prov_summary = {"error": "report_failed"}

        return CycleResult(
            cycle_id=cid,
            input=input_text,
            loop_report=report,
            trace_hash=start_entry.hash,
            monitoring_id=monitoring_id,
            registry_snapshot=snap,
            provenance_summary=prov_summary,
        )

    def state(self) -> dict:
        return {
            "cycles_executed": self._cycle_count,
            "loop_history": len(self._loop.history()),
            "active_monitor": self._active_monitor,
            "trace_valid": self._trace.verify(),
            "registry_snapshot": self._registry.snapshot() if self._registry else None,
            "provenance": self._provenance.report() if self._provenance else None,
        }

    def reset(self) -> None:
        self._active_monitor = None