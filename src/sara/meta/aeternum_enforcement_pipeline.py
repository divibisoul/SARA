"""AETERNUM M8 — enforcement pipeline over real SARA governance.

The pipeline never reports execution success unless a real executor is
injected and the governance gate accepts the proposal.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sara.contracts.base import CyclePhase, CycleRole, ModuleStatus
from sara.governance.governed_sara import GovernedSARA
from sara.monitoring.decision_trace import DecisionTrace
from sara.monitoring.governance import GovernanceBackend


@dataclass(frozen=True)
class EnforcementResult:
    status: str
    execution: str
    action: str
    detail: dict[str, Any]


class AeternumEnforcementPipelineModule:
    NAME = "AeternumEnforcementPipeline"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.GOVERNANCE
    DEPENDENCIES = ("GovernedSARA", "GovernanceBackend", "DecisionTrace")
    CYCLE_PHASES = (CyclePhase.GOVERNANCE,)

    STAGES = ("validate", "authorize", "execute", "verify")

    def __init__(
        self,
        governed_sara: GovernedSARA | None,
        governance: GovernanceBackend,
        trace: DecisionTrace,
        executor: Callable[[str, dict[str, Any]], Any] | None = None,
    ) -> None:
        self._governed_sara = governed_sara
        self._governance = governance
        self._trace = trace
        self._executor = executor

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [phase.value for phase in self.CYCLE_PHASES],
            "executor_bound": self._executor is not None,
            "governance_bound": self._governed_sara is not None,
        }

    def execute(
        self,
        action: str,
        params: dict[str, Any],
        proposal: dict[str, Any],
        ctx: Any = None,
    ) -> EnforcementResult:
        self._trace.log(
            {
                "event": "enforcement_requested",
                "action": action,
                "proposal_name": proposal.get("name", "unknown"),
            }
        )

        if self._governed_sara is None:
            return EnforcementResult(
                "governance_unbound",
                "not_claimed",
                action,
                {"stage": "authorize", "reason": "GovernedSARA not connected"},
            )

        if self._executor is None:
            return EnforcementResult(
                "handler_unbound",
                "not_claimed",
                action,
                {"stage": "execute", "reason": "real executor not connected"},
            )

        governance = self._governed_sara.assimilate(proposal, ctx=ctx)
        self._governance.register_decision(
            {
                "event": "enforcement_authorization",
                "action": action,
                "accepted": governance.accepted,
                "reasons": list(governance.reasons),
            }
        )

        if not governance.accepted:
            return EnforcementResult(
                "denied",
                "real",
                action,
                {
                    "stage": "authorize",
                    "accepted": False,
                    "reasons": list(governance.reasons),
                },
            )

        try:
            execution_result = self._executor(action, dict(params))
        except Exception as exc:
            self._trace.log(
                {
                    "event": "enforcement_failed",
                    "action": action,
                    "error": str(exc),
                }
            )
            return EnforcementResult(
                "failed",
                "real",
                action,
                {"stage": "execute", "error": str(exc)},
            )

        self._trace.log(
            {
                "event": "enforcement_completed",
                "action": action,
            }
        )
        self._governance.register_decision(
            {
                "event": "enforcement_completed",
                "action": action,
            }
        )

        return EnforcementResult(
            "completed",
            "real",
            action,
            {
                "stage": "verify",
                "executor_result": execution_result,
                "trace_integrity": self._trace.verify(),
                "governance_integrity": self._governance.verify_integrity(),
            },
        )

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record(
                "governance",
                self.NAME,
                True,
                executor_bound=self._executor is not None,
                governance_bound=self._governed_sara is not None,
            )
