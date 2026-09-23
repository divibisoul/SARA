"""AETERNUM M8 — governance report adapter over existing SARA authorities.

No second governance engine is introduced. GovernanceBackend and DecisionTrace
remain the authoritative local implementations.
"""
from __future__ import annotations

from typing import Any

from sara.contracts.base import CyclePhase, CycleRole, ModuleStatus
from sara.monitoring.decision_trace import DecisionTrace
from sara.monitoring.governance import GovernanceBackend


class AeternumGovernanceReportModule:
    NAME = "AeternumGovernanceReport"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.MONITORING
    DEPENDENCIES = ("GovernanceBackend", "DecisionTrace")
    CYCLE_PHASES = (CyclePhase.MONITORING, CyclePhase.GOVERNANCE)

    def __init__(
        self,
        governance: GovernanceBackend,
        trace: DecisionTrace,
    ) -> None:
        self._governance = governance
        self._trace = trace

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [phase.value for phase in self.CYCLE_PHASES],
            "execution_authority": "SARA:GovernanceBackend+DecisionTrace",
        }

    def report(self) -> dict[str, Any]:
        snapshot = self._governance.snapshot()
        decisions = self._governance.decisions()
        return {
            "status": "completed",
            "execution": "real",
            "snapshot": {
                "ts": snapshot.ts,
                "modules": dict(snapshot.modules),
                "decision_count": snapshot.last_decisions,
            },
            "governance_chain_integrity": self._governance.verify_integrity(),
            "decision_trace_integrity": self._trace.verify(),
            "decision_trace_entries": len(self._trace.query()),
            "recent_decisions": decisions[-10:],
        }

    def emit_trace(self, ctx) -> None:
        report = self.report()
        if hasattr(ctx, "record"):
            ctx.record(
                "monitoring",
                self.NAME,
                True,
                execution="real",
                governance_chain_integrity=report["governance_chain_integrity"],
                decision_trace_integrity=report["decision_trace_integrity"],
            )
