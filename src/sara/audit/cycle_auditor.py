"""SARA — Auditoria de ciclo.
Status: IMPLEMENTED.
"""
from __future__ import annotations
from dataclasses import dataclass
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


@dataclass
class InvariantResult:
    name: str
    ok: bool
    detail: str = ""


class CycleAuditor:
    NAME = "CycleAuditor"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.MONITORING
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.AUDIT, CyclePhase.VALIDATION, CyclePhase.MONITORING)

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
        }

    def check(self, ctx, cycle: dict) -> list[dict]:
        seen = {s.phase for s in ctx.steps}
        required = (
            "ingestion", "audit", "regeneration", "identity",
            "ethics", "strategy", "execution", "validation",
            "persistence", "snapshot", "monitoring", "governance",
        )
        results = [
            InvariantResult(f"phase_executed::{p}", p in seen,
                            "ok" if p in seen else "faltou")
            for p in required
        ]
        execution = "execution" in seen
        results.append(InvariantResult(
            "execution_implies_persistence",
            not execution or "persistence" in seen,
            "ok" if not execution or "persistence" in seen else "execução sem persistência",
        ))
        results.append(InvariantResult(
            "execution_implies_snapshot",
            not execution or "snapshot" in seen,
            "ok" if not execution or "snapshot" in seen else "execução sem snapshot",
        ))
        if cycle.get("aborted_at"):
            results.append(InvariantResult(
                "abort_has_reason", bool(cycle.get("abort_reason")),
                cycle.get("abort_reason", "sem motivo"),
            ))
        return [{"name": r.name, "ok": r.ok, "detail": r.detail} for r in results]

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("monitoring", self.NAME, True)
