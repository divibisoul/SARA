"""SARA-hosted Expert Mode policy adapter.

The original UI toggle is a presentation concern. In the federated
architecture, the authoritative state change is recorded by existing
GovernanceBackend and DecisionTrace instances. No second governance engine is
created here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sara.contracts.base import CyclePhase, CycleRole, ModuleStatus
from sara.monitoring.decision_trace import DecisionTrace
from sara.monitoring.governance import GovernanceBackend


@dataclass(frozen=True)
class ExpertModeState:
    enabled: bool
    changed_at: str | None
    actor: str | None
    reason: str | None


class ExpertModeToggleModule:
    NAME = "ExpertModeToggleModule"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.GOVERNANCE
    CYCLE_PHASES = (CyclePhase.GOVERNANCE, CyclePhase.MONITORING)
    DEPENDENCIES = ("GovernanceBackend", "DecisionTrace")

    def __init__(
        self,
        governance: GovernanceBackend,
        trace: DecisionTrace,
        initial_enabled: bool = False,
    ) -> None:
        self._governance = governance
        self._trace = trace
        self._active = False
        self._state = ExpertModeState(
            enabled=bool(initial_enabled),
            changed_at=None,
            actor=None,
            reason=None,
        )

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [phase.value for phase in self.CYCLE_PHASES],
            "active": self._active,
            "enabled": self._state.enabled,
            "authoritative_store": "SARA:GovernanceBackend+DecisionTrace",
        }

    def activate(self) -> None:
        self._active = True

    def deactivate(self) -> None:
        self._active = False

    def is_active(self) -> bool:
        return self._active

    def is_enabled(self) -> bool:
        return self._state.enabled

    def state(self) -> ExpertModeState:
        return self._state

    def toggle(self, *, actor: str | None = None, reason: str | None = None) -> ExpertModeState:
        return self.set(
            not self._state.enabled,
            actor=actor,
            reason=reason or "expert_mode_toggle",
        )

    def set(
        self,
        enabled: bool,
        *,
        actor: str | None = None,
        reason: str | None = None,
    ) -> ExpertModeState:
        if not self._active:
            raise RuntimeError("EXPERT_MODE_MODULE_INACTIVE")

        enabled = bool(enabled)
        changed_at = self._now()
        normalized_reason = reason.strip() if reason else None

        decision = {
            "event": "expert_mode_changed",
            "enabled": enabled,
            "actor": actor,
            "reason": normalized_reason,
        }
        trace_entry = self._trace.log(decision)
        self._governance.register_decision(
            {
                **decision,
                "trace_index": trace_entry.index,
            }
        )

        self._state = ExpertModeState(
            enabled=enabled,
            changed_at=changed_at,
            actor=actor,
            reason=normalized_reason,
        )
        return self._state

    @staticmethod
    def _now() -> str:
        from sara.infra.clock import now_iso

        return now_iso()

    def emit_trace(self, ctx: Any) -> None:
        if hasattr(ctx, "record"):
            ctx.record(
                "governance",
                self.NAME,
                True,
                active=self._active,
                enabled=self._state.enabled,
            )
