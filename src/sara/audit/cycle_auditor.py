"""SARA — Auditoria: CycleAuditor.
Status: IMPLEMENTED.
"""
from __future__ import annotations
from dataclasses import dataclass
from sara.contracts.base import CyclePhase
from sara.contracts.lifecycle import CANONICAL_ORDER


@dataclass
class InvariantResult:
    name: str
    ok: bool
    detail: str = ""


class CycleAuditor:
    NAME = "CycleAuditor"
    VERSION = "1.0"

    def check(self, ctx, cycle: dict) -> list[dict]:
        phases_seen = set()
        for s in ctx.steps:
            phases_seen.add(s.phase)
        for p in cycle.get("phases", {}).keys():
            phases_seen.add(p)

        results: list[InvariantResult] = []
        obrigatorias = ("ingestion", "audit", "regeneration",
                        "identity", "ethics", "strategy",
                        "execution", "persistence")
        for req in obrigatorias:
            results.append(InvariantResult(
                name=f"phase_executed::{req}",
                ok=(req in phases_seen),
                detail="ok" if req in phases_seen else "faltou",
            ))

        executed = "execution" in phases_seen
        persisted = "persistence" in phases_seen
        results.append(InvariantResult(
            name="execution_implies_persistence",
            ok=(not executed) or persisted,
            detail="ok" if (not executed or persisted) else "execução sem persistência",
        ))

        snapshotted = "snapshot" in phases_seen
        results.append(InvariantResult(
            name="execution_implies_snapshot",
            ok=(not executed) or snapshotted,
            detail="ok" if (not executed or snapshotted) else "execução sem snapshot",
        ))

        aborted = "aborted_at" in cycle
        if aborted:
            results.append(InvariantResult(
                name="abort_has_reason",
                ok=bool(cycle.get("abort_reason")),
                detail=cycle.get("abort_reason", "sem motivo"),
            ))

        return [
            {"name": r.name, "ok": r.ok, "detail": r.detail}
            for r in results
        ]