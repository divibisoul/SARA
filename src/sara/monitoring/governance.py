"""SARA — Monitoramento: Governance backend.
Status: IMPLEMENTED (backend) | PENDING_INFRASTRUCTURE (UI)
"""
from __future__ import annotations
from dataclasses import dataclass
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.clock import now_iso
from sara.infra.hashing import chain_hash


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
        self._decision_chain: list[str] = []

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "ui_ready": self.is_ui_ready(),
        }

    def register_decision(self, decision: dict) -> None:
        payload = {"ts": now_iso(), **dict(decision)}
        previous = self._decision_chain[-1] if self._decision_chain else "GENESIS"
        current = chain_hash(previous, payload)
        payload["integrity"] = current
        self._decisions.append(payload)
        self._decision_chain.append(current)

    def snapshot(self) -> SystemSnapshot:
        return SystemSnapshot(now_iso(), dict(self._modules), len(self._decisions))

    def verify_integrity(self) -> bool:
        if len(self._decisions) != len(self._decision_chain):
            return False
        previous = "GENESIS"
        for decision, chain_value in zip(self._decisions, self._decision_chain):
            payload = {
                k: v for k, v in decision.items()
                if k != "integrity"
            }
            expected = chain_hash(previous, payload)
            if expected != chain_value or decision.get("integrity") != chain_value:
                return False
            previous = chain_value
        return True

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
                       decisions_count=len(self._decisions),
                       chain_integrity=self.verify_integrity())