"""SARA — Regeneração: núcleo operacional fail-closed.
Status: IMPLEMENTED.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from sara.contracts import ModuleRegistry, CyclePhase, CycleContext, TraceSink
from sara.contracts.base import ModuleStatus, CycleRole
from sara.contracts.invariants import InvariantValidator
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
from sara.monitoring.execution_report import ExecutionReport, PhaseEvidence
from sara.regeneration.regenerative_state import CycleState, RegenerativeState


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
    execution_report: dict = field(default_factory=dict)


class _Aborted(Exception):
    def __init__(self, phase: str, reason: str) -> None:
        self.phase = phase
        self.reason = reason
        super().__init__(f"{phase}:{reason}")


class RegenerativeLoop:
    NAME = "RegenerativeLoop"
    VERSION = "5.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.REGENERATION
    DEPENDENCIES = (
        "ARA", "ETR", "ITR", "IdentityCore", "RegenerativeMemory",
        "TemporalVectorDB", "DNA_Tags", "EthicalFilterChain",
        "EmergencyRollback", "DecisionTrace", "ProvenanceTracker",
        "ModuleRegistry", "GovernanceBackend", "CycleAuditor",
    )
    CYCLE_PHASES = tuple(CyclePhase)

    def __init__(
        self, ara: ARA, etr: ETR, itr: ITR, identity: IdentityCore,
        memory: RegenerativeMemory, temporal: TemporalVectorDB, dna: DNA_Tags,
        filters: EthicalFilterChain, rollback: EmergencyRollback,
        decision_trace: Any = None, provenance: Any = None,
        registry: ModuleRegistry | None = None, governance_backend: Any = None,
        cycle_auditor: Any = None, max_cycles: int = 3,
    ) -> None:
        self._ara, self._etr, self._itr = ara, etr, itr
        self._identity, self._memory = identity, memory
        self._temporal, self._dna = temporal, dna
        self._filters, self._rollback = filters, rollback
        self._trace, self._prov = decision_trace, provenance
        self._registry, self._gov_backend = registry, governance_backend
        self._auditor, self._max_cycles = cycle_auditor, max(1, max_cycles)
        self._history: list[LoopReport] = []
        self._invariants = InvariantValidator()

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "max_cycles": self._max_cycles,
        }

    def _preflight(self, ctx: CycleContext) -> None:
        report = self._invariants.validate_context_pre_execution(ctx)
        if not report.ok:
            raise _Aborted("PREFLIGHT", ";".join(report.blocking_failures))
        if self._registry is not None:
            registry_report = self._invariants.validate_registry(self._registry)
            if not registry_report.ok:
                raise _Aborted("PREFLIGHT", ";".join(registry_report.blocking_failures))
        if self._trace is not None and not self._trace.verify():
            raise _Aborted("PREFLIGHT", "decision_trace_integrity_failed")

    def run(self, input_text: str, cycle_id: str | None = None) -> LoopReport:
        cid = cycle_id or f"cycle-{now_iso()}"
        sink = TraceSink(self._trace, self._temporal, self._prov)
        ctx = CycleContext(cid, str(input_text), str(input_text), sink)
        self._preflight(ctx)

        report = LoopReport(
            cycle_id=cid, input=str(input_text)[:200], cycles=[],
            final_state=str(input_text), rollback_performed=False, converged=False,
        )
        report.filter_classification = [r.__dict__ for r in self._filters.classify(ctx.current)]

        state = RegenerativeState(cid)
        state.transition(CycleState.PREFLIGHT, "invariants_ok", now_iso())

        for idx in range(1, self._max_cycles + 1):
            state.iteration = idx
            state.transition(CycleState.RUNNING, f"iteration_{idx}", now_iso())
            cycle = {"idx": idx, "phases": {}}
            pre_state = {"cycle": idx, "input": ctx.current, "ts": now_iso()}
            pre_hash = self._rollback.capture(f"{cid}::{idx}::pre", pre_state, scope="cycle")
            cycle["pre_hash"] = pre_hash
            try:
                self._run_phases_canonical(ctx, cycle, idx)
                invariant_report = self._invariants.validate_cycle(ctx, cycle)
                cycle["invariants"] = invariant_report.as_dict()
                if not invariant_report.ok:
                    raise _Aborted("VALIDATION", ";".join(invariant_report.blocking_failures))

                post_etr = self._etr.validate(ctx.current, mode="default")
                post_flaws = self._collect_flaws(ctx.current)
                cycle["post_validation"] = {
                    "approved": post_etr.approved,
                    "reason": post_etr.reason,
                    "flaws": [f.kind for f in post_flaws],
                }

                converged = (
                    post_etr.approved
                    and not post_flaws
                    and bool(ctx.artifacts.get("execution_ok", False))
                    and invariant_report.ok
                )
                cycle["converged"] = converged
                report.cycles.append(cycle)

                if converged:
                    state.transition(CycleState.CONVERGED, "all_criteria_satisfied", now_iso())
                    report.converged = True
                    report.final_state = ctx.current
                    break

                state.transition(CycleState.REGENERATING, "residual_flaws", now_iso())
                if idx == self._max_cycles:
                    restored = self._rollback.restore(pre_hash)
                    report.rollback_performed = restored.restored
                    if restored.restored:
                        ctx.current = restored.state.get("input", ctx.input)
                        state.transition(CycleState.ROLLED_BACK, "max_iterations_without_convergence", now_iso())
            except _Aborted as exc:
                ctx.abort(f"{exc.phase}:{exc.reason}")
                cycle["aborted_at"], cycle["abort_reason"] = exc.phase, exc.reason
                restored = self._rollback.restore(pre_hash)
                report.rollback_performed = restored.restored
                if restored.restored:
                    ctx.current = restored.state.get("input", ctx.input)
                state.transition(CycleState.ROLLED_BACK if restored.restored else CycleState.ABORTED,
                                 exc.reason, now_iso())
                report.cycles.append(cycle)
                break
            except Exception as exc:
                ctx.abort(f"UNEXPECTED:{type(exc).__name__}:{exc}")
                cycle["aborted_at"], cycle["abort_reason"] = "UNEXPECTED", str(exc)
                restored = self._rollback.restore(pre_hash)
                report.rollback_performed = restored.restored
                if restored.restored:
                    ctx.current = restored.state.get("input", ctx.input)
                state.transition(CycleState.ROLLED_BACK if restored.restored else CycleState.ABORTED,
                                 str(exc), now_iso())
                report.cycles.append(cycle)
                break

        state.transition(CycleState.COMPLETED, "cycle_finished", now_iso())
        report.final_state = ctx.current
        report.invariants = [
            x for c in report.cycles for x in c.get("invariants", {}).get("checks", [])
        ]
        report.temporal_ids = [
            s.info["temporal_id"] for s in ctx.steps if "temporal_id" in s.info
        ]
        report.context_steps = [
            {"phase": s.phase, "module": s.module, "ok": s.ok, "info": s.info, "ts": s.ts}
            for s in ctx.steps
        ]

        er = ExecutionReport(
            cycle_id=cid,
            status="CONVERGED" if report.converged else ("ROLLED_BACK" if report.rollback_performed else "ABORTED"),
            invariants=report.invariants,
            artifacts={**ctx.artifacts, "state": state.state.value,
                       "transitions": [t.__dict__ for t in state.transitions]},
            trace_integrity=self._trace.verify() if self._trace is not None else False,
        )
        er.phases = [
            PhaseEvidence(s.phase, s.module, s.ok, s.info, s.ts) for s in ctx.steps
        ]
        report.execution_report = er.finalize().as_dict()
        self._history.append(report)
        return report

    def _collect_flaws(self, text: str) -> list[Any]:
        flaws = list(self._ara.detect(text))
        structural = getattr(self._ara, "detect_structural", lambda _t: [])(text)
        relational = getattr(self._ara, "detect_relational", lambda _t: [])(text)
        return flaws + list(relational) + list(structural)

    def _run_phases_canonical(self, ctx: CycleContext, cycle: dict, idx: int) -> None:
        self._phase_ingestion(ctx, cycle, idx)
        self._phase_audit(ctx, cycle)
        self._phase_regeneration(ctx, cycle)
        self._phase_identity(ctx, cycle, idx)
        etr_result = self._phase_ethics(ctx, cycle)
        strategy = self._phase_strategy(ctx, cycle, idx)
        result = self._phase_execution(ctx, cycle, strategy)
        self._phase_validation(ctx, cycle, etr_result)
        self._phase_persistence(ctx, cycle, idx, result)
        self._phase_snapshot(ctx, cycle, idx)
        self._phase_monitoring(ctx, cycle)
        self._phase_governance(ctx, cycle)

    def _record(self, ctx, phase, module, ok, **info):
        ctx.record(phase.value if isinstance(phase, CyclePhase) else phase, module, ok, **info)

    def _phase_ingestion(self, ctx, cycle, idx):
        guard = self._dna.guard(f"cycle_{idx}", ctx.current)
        self._record(ctx, CyclePhase.INGESTION, "DNA_Tags", not guard.blocked,
                     tags=list(guard.tags), blocked=guard.blocked)
        cycle["phases"]["ingestion"] = {"blocked": guard.blocked, "tags": list(guard.tags)}
        if guard.blocked:
            raise _Aborted("INGESTION", "dna_block")

    def _phase_audit(self, ctx, cycle):
        lexical = list(self._ara.detect(ctx.current))
        structural = list(getattr(self._ara, "detect_structural", lambda _t: [])(ctx.current))
        relational = list(getattr(self._ara, "detect_relational", lambda _t: [])(ctx.current))
        cycle["_flaws"] = lexical + relational
        cycle["phases"]["audit"] = {
            "lexical": [f.kind for f in lexical],
            "structural": [f.kind for f in structural],
            "relational": [f.kind for f in relational],
        }
        self._record(ctx, CyclePhase.AUDIT, "ARA", True, **cycle["phases"]["audit"])

    def _phase_regeneration(self, ctx, cycle):
        flaws = cycle.get("_flaws", [])
        if not flaws:
            self._record(ctx, CyclePhase.REGENERATION, "ARA", True, applied="not_needed")
            cycle["phases"]["regeneration"] = {"applied": "not_needed"}
            return
        if hasattr(self._ara, "regenerate_semantic"):
            regen = self._ara.regenerate_semantic(ctx.current, flaws)
        else:
            regen = self._ara.regenerate(ctx.current, flaws)
        before = ctx.current
        ctx.current = regen.transformed
        ctx.register_artifact("regeneration_integrity", regen.integrity_hash)
        cycle["phases"]["regeneration"] = {
            "applied": list(regen.plan_steps),
            "preserved_length": regen.preserved_length,
            "changed": before != ctx.current,
            "integrity": regen.integrity_hash,
        }
        self._record(ctx, CyclePhase.REGENERATION, "ARA", True, **cycle["phases"]["regeneration"])

    def _phase_identity(self, ctx, cycle, idx):
        ident = self._identity.participate(f"cycle_{idx}", ctx.current)
        cycle["phases"]["identity"] = {
            "approved": ident.identity_approved,
            "violations": list(ident.violations),
        }
        self._record(ctx, CyclePhase.IDENTITY, "IdentityCore", ident.identity_approved,
                     **cycle["phases"]["identity"])
        if not ident.identity_approved:
            raise _Aborted("IDENTITY", "identity_block")

    def _phase_ethics(self, ctx, cycle):
        base = self._etr.validate(ctx.current, mode="default")
        multi = getattr(self._etr, "validate_multi_framework", None)
        multi_result = multi(ctx.current) if multi else None
        approved = base.approved and (multi_result.approved if multi_result else True)
        cycle["phases"]["ethics"] = {
            "approved": approved,
            "base_reason": base.reason,
            "consensus": multi_result.consensus_score if multi_result else None,
            "dissenting": list(multi_result.dissenting_frameworks) if multi_result else [],
        }
        self._record(ctx, CyclePhase.ETHICS, "ETR", approved, **cycle["phases"]["ethics"])
        if not approved:
            raise _Aborted("ETHICS", base.reason if not base.approved else "multi_framework_rejected")
        return base

    def _phase_strategy(self, ctx, cycle, idx):
        if hasattr(self._itr, "generate_strategic"):
            strategy = self._itr.generate_strategic(ctx.current, {"cycle": idx})
            cycle["phases"]["strategy"] = {
                "type": "StrategicPlan",
                "phases": len(strategy.phases),
                "criteria": list(strategy.convergence_criteria),
            }
        else:
            strategy = self._itr.generate(ctx.current, context={"cycle": idx})
            cycle["phases"]["strategy"] = {"type": "Strategy", "variant": strategy.variant}
        self._record(ctx, CyclePhase.STRATEGY, "ITR", True, **cycle["phases"]["strategy"])
        return strategy

    def _phase_execution(self, ctx, cycle, strategy):
        if hasattr(strategy, "phases") and hasattr(self._itr, "execute_composed"):
            result = self._itr.execute_composed(strategy)
            transformed = result.transformed
            ok = not result.rollback_triggered
            info = {"composed": True, "metrics": result.metrics,
                    "rollback_triggered": result.rollback_triggered}
        else:
            result = self._itr.execute(strategy)
            transformed = result.transformed
            ok = True
            info = {"steps": list(result.steps_applied), "metrics": result.metrics}
        ctx.current = transformed
        ctx.register_artifact("final_output", transformed)
        ctx.flags["execution_ok"] = ok
        cycle["phases"]["execution"] = {"ok": ok, **info}
        self._record(ctx, CyclePhase.EXECUTION, "ITR", ok, **cycle["phases"]["execution"])
        if not ok:
            raise _Aborted("EXECUTION", "execution_rollback_triggered")
        return result

    def _phase_validation(self, ctx, cycle, etr_result):
        result = self._etr.validate(ctx.current, mode="default")
        cycle["phases"]["validation"] = {
            "approved": result.approved,
            "reason": result.reason,
            "previous_ethics_approved": etr_result.approved,
        }
        self._record(ctx, CyclePhase.VALIDATION, "ETR", result.approved,
                     **cycle["phases"]["validation"])
        if not result.approved:
            raise _Aborted("VALIDATION", result.reason)

    def _phase_persistence(self, ctx, cycle, idx, result):
        rid = self._temporal.insert({
            "cycle_id": ctx.cycle_id, "iteration": idx,
            "input": ctx.input, "state": ctx.current,
            "execution": getattr(result, "metrics", {}),
        })
        self._memory.store({
            "cycle_id": ctx.cycle_id, "iteration": idx,
            "state": ctx.current, "temporal_id": rid,
        }, label=f"{ctx.cycle_id}::iteration::{idx}")
        cycle["phases"]["persistence"] = {"temporal_id": rid}
        self._record(ctx, CyclePhase.PERSISTENCE, "RegenerativeMemory", True,
                     temporal_id=rid)

    def _phase_snapshot(self, ctx, cycle, idx):
        snap = self._rollback.capture(
            f"{ctx.cycle_id}::{idx}::post",
            {"cycle_id": ctx.cycle_id, "iteration": idx, "state": ctx.current},
            scope="full",
        )
        cycle["phases"]["snapshot"] = {"snapshot_hash": snap}
        self._record(ctx, CyclePhase.SNAPSHOT, "EmergencyRollback", True,
                     snapshot_hash=snap)

    def _phase_monitoring(self, ctx, cycle):
        if self._gov_backend is not None and hasattr(self._gov_backend, "register_decision"):
            self._gov_backend.register_decision({
                "event": "cycle_monitoring",
                "cycle_id": ctx.cycle_id,
                "phases": list(cycle["phases"].keys()),
            })
        self._record(ctx, CyclePhase.MONITORING, "RegenerativeLoop", True,
                     trace_valid=self._trace.verify() if self._trace is not None else False)

    def _phase_governance(self, ctx, cycle):
        self._record(ctx, CyclePhase.GOVERNANCE, "RegenerativeLoop", True,
                     pending_infrastructure="not_executed")
    
    def history(self) -> list[LoopReport]:
        return list(self._history)

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("regeneration", self.NAME, True, version=self.VERSION)
