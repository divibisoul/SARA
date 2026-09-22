"""SARA — Regeneração: RegenerativeLoop v4.
Status: IMPLEMENTED (deep, canonical order, dispatch amplo).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sara.contracts import (
    ModuleRegistry, CyclePhase, CycleContext, TraceSink, CANONICAL_ORDER,
)
from sara.core.ara import ARA
from sara.core.etr import ETR
from sara.core.itr import ITR
from sara.security.identity_core import IdentityCore
from sara.security.emergency_rollback import EmergencyRollback
from sara.security.ethical_filter_chain import EthicalFilterChain
from sara.memory.regenerative_memory import RegenerativeMemory
from sara.memory.temporal_vector_db import TemporalVectorDB
from sara.memory.dna_tags import DNA_Tags
from sara.infra.clock import now_iso


@dataclass
class LoopReport:
    cycle_id: str
    input: str
    cycles: list[dict]
    final_state: Any
    rollback_performed: bool
    converged: bool
    filter_classification: list = field(default_factory=list)
    temporal_ids: list = field(default_factory=list)
    context_steps: list = field(default_factory=list)
    invariants: list = field(default_factory=list)


class _Aborted(Exception):
    def __init__(self, phase: str, reason: str) -> None:
        self.phase = phase
        self.reason = reason
        super().__init__(f"{phase}:{reason}")


class RegenerativeLoop:
    NAME = "RegenerativeLoop"
    VERSION = "4.0"

    def __init__(
        self,
        ara: ARA,
        etr: ETR,
        itr: ITR,
        identity: IdentityCore,
        memory: RegenerativeMemory,
        temporal: TemporalVectorDB,
        dna: DNA_Tags,
        filters: EthicalFilterChain,
        rollback: EmergencyRollback,
        decision_trace: Any = None,
        provenance: Any = None,
        registry: ModuleRegistry | None = None,
        governance_backend: Any = None,
        cycle_auditor: Any = None,
        max_cycles: int = 3,
    ) -> None:
        self._ara = ara
        self._etr = etr
        self._itr = itr
        self._identity = identity
        self._memory = memory
        self._temporal = temporal
        self._dna = dna
        self._filters = filters
        self._rollback = rollback
        self._trace = decision_trace
        self._prov = provenance
        self._registry = registry
        self._gov_backend = governance_backend
        self._auditor = cycle_auditor
        self._max_cycles = max_cycles
        self._history: list[LoopReport] = []

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "registry_attached": self._registry is not None,
            "governance_attached": self._gov_backend is not None,
            "provenance_attached": self._prov is not None,
            "max_cycles": self._max_cycles,
        }

    def run(self, input_text: str, cycle_id: str | None = None) -> LoopReport:
        cid = cycle_id or f"cycle-{now_iso()}"
        sink = TraceSink(
            decision_trace=self._trace,
            temporal=self._temporal,
            provenance=self._prov,
        )
        ctx = CycleContext(
            cycle_id=cid,
            input=str(input_text),
            current=str(input_text),
            sink=sink,
        )

        report = LoopReport(
            cycle_id=cid,
            input=str(input_text)[:200],
            cycles=[],
            final_state=None,
            rollback_performed=False,
            converged=False,
        )

        report.filter_classification = [
            r.__dict__ for r in self._filters.classify(ctx.current)
        ]

        for idx in range(1, self._max_cycles + 1):
            cycle: dict = {"idx": idx, "phases": {}}
            pre_state = {"cycle": idx, "input": ctx.current, "ts": now_iso()}
            pre_hash = self._rollback.capture(f"cycle_{idx}_pre", pre_state, scope="cycle")
            cycle["pre_hash"] = pre_hash

            try:
                self._run_phases_canonical(ctx, cycle, idx, pre_hash)
            except _Aborted as ab:
                cycle["aborted_at"] = ab.phase
                cycle["abort_reason"] = ab.reason
                restored = self._rollback.restore(pre_hash)
                cycle["rollback_restored"] = restored.restored
                report.rollback_performed = True
                report.cycles.append(cycle)
                if restored.restored:
                    report.final_state = restored.state
                break

            post_flaws = self._ara.detect(ctx.current)
            if not post_flaws:
                cycle["converged"] = True
                report.converged = True
                report.final_state = ctx.artifacts.get("final_output", ctx.current)
                if self._auditor is not None:
                    report.invariants = self._auditor.check(ctx, cycle)
                report.cycles.append(cycle)
                break

            cycle["converged"] = False
            report.cycles.append(cycle)

        report.temporal_ids = [
            s.info.get("temporal_id")
            for s in ctx.steps
            if "temporal_id" in s.info
        ]
        report.context_steps = [
            {"phase": s.phase, "module": s.module, "ok": s.ok, "info": s.info}
            for s in ctx.steps
        ]
        self._history.append(report)
        return report

    def _run_phases_canonical(self, ctx, cycle, idx, pre_hash):
        self._phase_ingestion(ctx, cycle, idx)
        self._dispatch_emit_trace(ctx, CyclePhase.INGESTION)

        self._phase_audit(ctx, cycle)
        self._dispatch_emit_trace(ctx, CyclePhase.AUDIT)

        self._phase_regeneration(ctx, cycle)
        self._dispatch_emit_trace(ctx, CyclePhase.REGENERATION)

        self._phase_identity(ctx, cycle, idx)
        self._dispatch_emit_trace(ctx, CyclePhase.IDENTITY)

        etr_res = self._phase_ethics(ctx, cycle)
        self._dispatch_emit_trace(ctx, CyclePhase.ETHICS)

        strategy = self._phase_strategy(ctx, cycle, idx)
        self._dispatch_emit_trace(ctx, CyclePhase.STRATEGY)

        result = self._phase_execution(ctx, cycle, strategy)
        self._dispatch_emit_trace(ctx, CyclePhase.EXECUTION)

        self._phase_validation(ctx, etr_res)
        self._dispatch_emit_trace(ctx, CyclePhase.VALIDATION)

        self._phase_persistence(ctx, cycle, idx, result)
        self._dispatch_emit_trace(ctx, CyclePhase.PERSISTENCE)

        self._phase_snapshot(ctx, cycle, idx)
        self._dispatch_emit_trace(ctx, CyclePhase.SNAPSHOT)

        self._phase_monitoring(ctx)
        self._dispatch_emit_trace(ctx, CyclePhase.MONITORING)

        self._phase_governance(ctx)
        self._dispatch_emit_trace(ctx, CyclePhase.GOVERNANCE)

    def _phase_ingestion(self, ctx, cycle, idx):
        guard = self._dna.guard(f"cycle_{idx}", ctx.current)
        ctx.record("ingestion", "DNA_Tags", not guard.blocked,
                   tags=list(guard.tags), blocked=guard.blocked)
        cycle["phases"]["ingestion"] = {"blocked": guard.blocked, "tags": list(guard.tags)}
        if guard.blocked:
            raise _Aborted("ingestion", "dna_block")

    def _phase_audit(self, ctx, cycle):
        flaws = self._ara.detect(ctx.current)
        ctx.record("audit", "ARA", True, flaws=[f.kind for f in flaws])
        cycle["phases"]["audit"] = {"flaws": [f.kind for f in flaws]}
        cycle["_flaws"] = flaws

    def _phase_regeneration(self, ctx, cycle):
        flaws = cycle.get("_flaws", [])
        if flaws:
            regen = self._ara.regenerate(ctx.current, flaws)
            ctx.current = regen.transformed
            ctx.record("regeneration", "ARA", True,
                       plan=list(regen.plan_steps), preserved=regen.preserved_length,
                       integrity=regen.integrity_hash)
            cycle["phases"]["regeneration"] = {
                "plan": list(regen.plan_steps), "preserved": regen.preserved_length,
            }
        else:
            ctx.record("regeneration", "ARA", True, applied="not_needed")
            cycle["phases"]["regeneration"] = {"applied": "not_needed"}

    def _phase_identity(self, ctx, cycle, idx):
        ident = self._identity.participate(f"cycle_{idx}", ctx.current)
        ctx.record("identity", "IdentityCore", ident.identity_approved,
                   violations=list(ident.violations))
        cycle["phases"]["identity"] = {"approved": ident.identity_approved}
        if not ident.identity_approved:
            raise _Aborted("identity", "identity_block")

    def _phase_ethics(self, ctx, cycle):
        etr_res = self._etr.validate(ctx.current, mode="default")
        ctx.record("ethics", "ETR", etr_res.approved, reason=etr_res.reason)
        cycle["phases"]["ethics"] = {"approved": etr_res.approved, "reason": etr_res.reason}
        if not etr_res.approved:
            raise _Aborted("ethics", etr_res.reason)
        return etr_res

    def _phase_strategy(self, ctx, cycle, idx):
        strategy = self._itr.generate(ctx.current, context={"cycle": idx})
        ctx.record("strategy", "ITR", True,
                   variant=strategy.variant, plan=list(strategy.plan))
        cycle["phases"]["strategy"] = {"variant": strategy.variant}
        return strategy

    def _phase_execution(self, ctx, cycle, strategy):
        result = self._itr.execute(strategy)
        ctx.current = result.transformed
        ctx.register_artifact("final_output", result.transformed)
        ctx.record("execution", "ITR", True,
                   steps=list(result.steps_applied), metrics=result.metrics)
        cycle["phases"]["execution"] = {"steps": list(result.steps_applied)}
        return result

    def _phase_validation(self, ctx, etr_res):
        cultural = etr_res.cultural
        ctx.record("validation", "ETR.cultural", True,
                   ubuntu=cultural[0].aligned if cultural else None,
                   buen=cultural[1].aligned if cultural else None)

    def _phase_persistence(self, ctx, cycle, idx, result):
        t_id = None
        for s in ctx.steps:
            if "temporal_id" in s.info:
                t_id = s.info["temporal_id"]
                break
        self._memory.store(
            {"cycle": idx, "input": ctx.current, "result": result.transformed,
             "temporal": t_id},
            label=f"{ctx.cycle_id}::cycle_{idx}",
        )
        ctx.record("persistence", "RegenerativeMemory", True)

    def _phase_snapshot(self, ctx, cycle, idx):
        snap_state = {"cycle_id": ctx.cycle_id, "idx": idx, "state": ctx.current}
        snap_hash = self._rollback.capture(f"{ctx.cycle_id}::{idx}_post", snap_state, scope="full")
        ctx.record("snapshot", "EmergencyRollback", True, snapshot=snap_hash[:12])

    def _phase_monitoring(self, ctx):
        if self._gov_backend is not None and hasattr(self._gov_backend, "register_decision"):
            self._gov_backend.register_decision({
                "event": "monitoring_snapshot",
                "cycle_id": ctx.cycle_id,
                "steps": len(ctx.steps),
            })

    def _phase_governance(self, ctx):
        ctx.record("governance", "RegenerativeLoop", True,
                   auto="not_executed_here")

    def _dispatch_emit_trace(self, ctx, phase: CyclePhase):
        if self._registry is None:
            return
        for m in self._registry.modules_for_phase(phase):
            if hasattr(m.instance, "emit_trace"):
                try:
                    m.instance.emit_trace(ctx)
                except Exception as exc:
                    ctx.record(phase.value, m.name, False, error=str(exc))

    def history(self) -> list[LoopReport]:
        return list(self._history)