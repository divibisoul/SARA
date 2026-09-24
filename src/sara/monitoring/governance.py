"""SARA — Monitoramento: Governance backend.
Status: IMPLEMENTED (backend) | PENDING_INFRASTRUCTURE (UI)
"""
from __future__ import annotations
from dataclasses import dataclass
import html
import json
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
        self._overrides: dict[int, dict] = {}
        self._override_records: list[dict] = []
        self._override_chain: list[str] = []

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
        return [
            {
                **decision,
                **(
                    {"override": dict(self._overrides[index])}
                    if index in self._overrides else {}
                ),
            }
            for index, decision in enumerate(self._decisions)
            if since is None or decision["ts"] >= since
        ]

    def override(self, decision_id: int, action: str) -> dict:
        if decision_id < 0 or decision_id >= len(self._decisions):
            return {"ok": False, "reason": "decision_id_out_of_range"}
        action = str(action).strip()
        if not action:
            return {"ok": False, "reason": "action_required"}
        override = {
            "decision_id": decision_id,
            "action": action,
            "ts": now_iso(),
        }
        previous = self._override_chain[-1] if self._override_chain else "GENESIS"
        current = chain_hash(previous, override)
        record = {**override, "integrity": current}
        self._override_records.append(record)
        self._overrides[decision_id] = dict(record)
        self._override_chain.append(current)
        return {
            "ok": True,
            "decision_id": decision_id,
            "override": dict(self._overrides[decision_id]),
            "decision_integrity_preserved": self.verify_integrity(),
            "override_chain_integrity": self.verify_override_integrity(),
        }

    def verify_override_integrity(self) -> bool:
        if len(self._override_chain) != len(self._override_records):
            return False
        previous = "GENESIS"
        for override in self._override_records:
            payload = {
                "decision_id": override["decision_id"],
                "action": override["action"],
                "ts": override["ts"],
            }
            expected = chain_hash(previous, payload)
            if expected != override.get("integrity"):
                return False
            previous = override["integrity"]
        return previous == (self._override_chain[-1] if self._override_chain else "GENESIS")

    def override_history(self) -> list[dict]:
        return [dict(item) for item in self._override_records]

    def is_ui_ready(self) -> bool:
        return True

    def render_html(self) -> str:
        """Renderização administrativa local; não depende de framework externo."""
        snapshot = self.snapshot()
        decisions = self.decisions()
        payload = {
            "timestamp": snapshot.ts,
            "modules": snapshot.modules,
            "decision_count": snapshot.last_decisions,
            "chain_integrity": self.verify_integrity(),
            "override_chain_integrity": self.verify_override_integrity(),
            "decisions": decisions,
        }
        serialized = html.escape(json.dumps(payload, ensure_ascii=False, indent=2))
        return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SARA Governance</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem;max-width:1100px}}
pre{{white-space:pre-wrap;background:#f4f4f4;padding:1rem;border-radius:.5rem}}
h1{{margin-bottom:.25rem}}</style></head>
<body><h1>SARA Governance</h1>
<p>Estado administrativo local, com cadeia de integridade verificável.</p>
<pre>{serialized}</pre>
</body></html>"""

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, True,
                       decisions_count=len(self._decisions),
                       chain_integrity=self.verify_integrity(),
                       override_chain_integrity=self.verify_override_integrity())