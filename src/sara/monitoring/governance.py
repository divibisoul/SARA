"""SARA — Monitoramento: Governance backend.
Status: IMPLEMENTED (backend) | PENDING_INFRASTRUCTURE (UI)
"""
from __future__ import annotations
from dataclasses import dataclass
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.clock import now_iso


@dataclass
class SystemSnapshot:
    ts: str
    modules: dict[str, str]
    last_decisions: int


class GovernanceBackend:
    NAME = "GovernanceBackend"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.MONITORING
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.GOVERNANCE, CyclePhase.MONITORING)

    def __init__(self, module_status: dict[str, str]) -> None:
        self._modules = dict(module_status)
        self._decisions: list[dict] = []

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "ui_ready": self.is_ui_ready(),
        }

    def register_decision(self, decision: dict) -> None:
        self._decisions.append({"ts": now_iso(), **decision})

    def snapshot(self) -> SystemSnapshot:
        return SystemSnapshot(now_iso(), dict(self._modules), len(self._decisions))

    def decisions(self, since: str | None = None) -> list[dict]:
        if since is None:
            return list(self._decisions)
        return [d for d in self._decisions if d["ts"] >= since]

    def override(self, decision_id: int, action: str) -> dict:
        if decision_id < 0 or decision_id >= len(self._decisions):
            return {"ok": False, "reason": "decision_id_out_of_range"}
        action = str(action).strip()
        if not action:
            return {"ok": False, "reason": "action_required"}
        decision = self._decisions[decision_id]
        decision["override"] = {
            "action": action,
            "ts": now_iso(),
        }
        return {
            "ok": True,
            "decision_id": decision_id,
            "override": dict(decision["override"]),
        }

    def is_ui_ready(self) -> bool:
        return False

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, True,
                       decisions_count=len(self._decisions))