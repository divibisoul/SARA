"""L6 — ERU Audit Module.

This is an adapter over SARA's existing GovernanceBackend and DecisionTrace.
It never invents an audit result. A run returns observed integrity, decision
counts and the governance snapshot available at execution time.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sara.monitoring.decision_trace import DecisionTrace
from sara.monitoring.governance import GovernanceBackend


@dataclass(frozen=True)
class ERUAuditResult:
    status: str
    chain_integrity: bool
    trace_integrity: bool
    decision_count: int
    modules: dict[str, str]
    reason: Optional[str] = None


class ERUAuditModule:
    NAME = "ERUAuditModule"
    VERSION = "1.0"

    def __init__(
        self,
        governance: GovernanceBackend | None = None,
        trace: DecisionTrace | None = None,
    ) -> None:
        # Deliberately unbound by default so this layer cannot create a second
        # governance authority. The existing SARA bootstrap must inject them.
        self._governance = governance
        self._trace = trace
        self._active = False

    def bind(self, governance: GovernanceBackend, trace: DecisionTrace) -> None:
        self._governance = governance
        self._trace = trace

    def activate(self) -> None:
        self._active = True

    def deactivate(self) -> None:
        self._active = False

    def run_audit(self) -> ERUAuditResult:
        if not self._active:
            return ERUAuditResult(
                status="INACTIVE",
                chain_integrity=False,
                trace_integrity=False,
                decision_count=0,
                modules={},
                reason="AUDITOR_INACTIVE",
            )
        if self._governance is None or self._trace is None:
            return ERUAuditResult(
                status="UNBOUND",
                chain_integrity=False,
                trace_integrity=False,
                decision_count=0,
                modules={},
                reason="GOVERNANCE_AND_TRACE_MUST_BE_BOUND",
            )

        snapshot = self._governance.snapshot()
        trace_ok = self._trace.verify()
        governance_ok = self._governance.verify_integrity()
        status = "HEALTHY" if trace_ok and governance_ok else "INCONSISTENT"

        return ERUAuditResult(
            status=status,
            chain_integrity=governance_ok,
            trace_integrity=trace_ok,
            decision_count=snapshot.last_decisions,
            modules=dict(snapshot.modules),
            reason=None if status == "HEALTHY" else "INTEGRITY_CHECK_FAILED",
        )


eruAuditModule = ERUAuditModule()
