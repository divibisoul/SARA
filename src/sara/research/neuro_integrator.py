"""SARA — Pesquisa: NeuroIntegrator v2.
Status: IMPLEMENTED (deep).
"""
from __future__ import annotations
from dataclasses import dataclass
from sara.security.emergency_rollback import EmergencyRollback
from sara.memory.regenerative_memory import RegenerativeMemory
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.clock import now_iso


@dataclass
class IntegrationReport:
    integration_id: str
    target_module: str
    ok: bool
    rollback_hash: str
    invariants: dict
    notes: str = ""


class NeuroIntegrator:
    NAME = "NeuroIntegrator"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.RESEARCH
    DEPENDENCIES = ("EmergencyRollback", "RegenerativeMemory", "ModuleRegistry")
    CYCLE_PHASES = (CyclePhase.SNAPSHOT, CyclePhase.PERSISTENCE)

    def __init__(self, rollback: EmergencyRollback,
                 memory: RegenerativeMemory, registry=None) -> None:
        self._rollback = rollback
        self._memory = memory
        self._registry = registry

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
        }

    def integrate(self, candidate: dict, target_module: str, ctx=None) -> IntegrationReport:
        snap_state = {"target": target_module, "candidate": candidate, "ts": now_iso()}
        snapshot_hash = self._rollback.capture(
            f"neuro_integrate_{candidate.get('name', 'unknown')}",
            snap_state, scope="full",
        )
        invariants: dict = {}
        try:
            if self._registry is not None:
                if self._registry.get(target_module) is None:
                    raise KeyError(f"target_module '{target_module}' não registrado")
                invariants["target_exists"] = True

            self._memory.store(
                {"event": "neuro_integration", "target": target_module,
                 "candidate": candidate, "ts": now_iso()},
                label=f"integrate::{target_module}",
            )
            invariants["memory_persisted"] = True

            if self._registry is not None:
                entry = self._registry.get(target_module)
                if entry is None:
                    raise KeyError(f"target_module '{target_module}' não registrado")
                invariants["target_status"] = entry.status.value
                invariants["target_still_registered"] = True

            if ctx is not None and hasattr(ctx, "record"):
                ctx.record("persistence", self.NAME, True,
                           target=target_module, snapshot=snapshot_hash[:12])

            return IntegrationReport(
                integration_id=snapshot_hash[:16], target_module=target_module,
                ok=True, rollback_hash=snapshot_hash, invariants=invariants,
                notes="fusão transacional concluída",
            )
        except Exception as exc:
            self._rollback.restore(snapshot_hash)
            invariants["rolled_back"] = True
            return IntegrationReport(
                integration_id=snapshot_hash[:16], target_module=target_module,
                ok=False, rollback_hash=snapshot_hash, invariants=invariants,
                notes=f"falha: {exc}",
            )

    def rollback(self, integration_id: str) -> dict:
        r = self._rollback.restore(integration_id)
        return {"restored": r.restored, "state": r.state}

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("persistence", self.NAME, True)