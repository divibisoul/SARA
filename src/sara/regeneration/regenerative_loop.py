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
from sara.contracts.context import CycleFusionState
from sara.infra.hashing import hash_json
from sara.regeneration.regenerative_state import CycleState, RegenerativeState
from sara.core.connected_runtime import ConnectedRuntime
from sara.meta.eru_engine import ERU_Engine


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
    fusion: dict | None = None


class _PhaseTraceProxy:
    def __init__(self, ctx: CycleContext, phase: CyclePhase) -> None:
        self._ctx = ctx
        self.cycle_id = ctx.cycle_id
        self.current = ctx.current
        self.sink = ctx.sink
        self.phase = phase

    def record(self, _phase: str, module: str, ok: bool, **info: Any) -> None:
        self._ctx.record(self.phase.value, module, ok, **info)

    def emit_decision(self, decision: dict) -> None:
        self._ctx.emit_decision(decision)


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
        connected_runtime: ConnectedRuntime | None = None,
        trinity: Any = None,
        eru: ERU_Engine | None = None,
    ) -> None:
        self._ara, self._etr, self._itr = ara, etr, itr
        self._identity, self._memory = identity, memory
        self._temporal, self._dna = temporal, dna
        self._filters, self._rollback = filters, rollback
        self._trace, self._prov = decision_trace, provenance
        self._registry, self._gov_backend = registry, governance_backend
        self._auditor, self._max_cycles = cycle_auditor, max(1, max_cycles)
        self._connected_runtime = connected_runtime
        self._trinity = trinity
        self._eru = eru
        self._history: list[LoopReport] = []
        self._invariants = InvariantValidator()

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "max_cycles": self._max_cycles,
            "eru_checkpointing": self._eru is not None,
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
        if self._prov is not None and hasattr(self._prov, "verify_integrity"):
            if not self._prov.verify_integrity():
                raise _Aborted("PREFLIGHT", "provenance_integrity_failed")

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
            if self._eru is not None:
                checkpoint = self._eru.checkpoint(
                    cid, idx, {"input": ctx.input, "current": ctx.current, "cycle": idx}
                )
                cycle["eru_checkpoint"] = checkpoint
                ctx.register_artifact(f"eru_checkpoint_{idx}", checkpoint)
            try:
                self._run_phases_canonical(ctx, cycle, idx)
                if self._auditor is not None and hasattr(self._auditor, "check"):
                    audit_results = self._auditor.check(ctx, cycle)
                    cycle["cycle_audit"] = audit_results
                    audit_failures = [r for r in audit_results if not r.get("ok", False)]
                    if audit_failures:
                        raise _Aborted(
                            "VALIDATION",
                            "cycle_auditor_failure:" + ";".join(
                                r.get("name", "unknown") for r in audit_failures
                            ),
                        )
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
                    and bool(ctx.flags.get("execution_ok", False))
                    and invariant_report.ok
                )
                cycle["converged"] = converged
                report.cycles.append(cycle)

                if converged:
                    if self._eru is not None and "eru_checkpoint" in cycle:
                        cycle["eru_checkpoint"]["final_verified"] = self._eru.verify_snapshot(
                            cycle["eru_checkpoint"]["name"]
                        )
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
                        ctx.fusion = None
                        state.transition(CycleState.ROLLED_BACK, "max_iterations_without_convergence", now_iso())
            except _Aborted as exc:
                ctx.abort(f"{exc.phase}:{exc.reason}")
                cycle["aborted_at"], cycle["abort_reason"] = exc.phase, exc.reason
                restored = self._rollback.restore(pre_hash)
                report.rollback_performed = restored.restored
                if restored.restored:
                    ctx.current = restored.state.get("input", ctx.input)
                    ctx.fusion = None

                # Divergência do espelho é tratada como evento regenerativo RGO:
                # rollback do estado inválido, registro do evento e nova iteração.
                if exc.reason == "fusion_integrity_failed" and idx < self._max_cycles:
                    ctx.flags.setdefault("rgo_regeneration_inputs", []).append({
                        "type": "FUSION_DIVERGENCE",
                        "cycle_id": ctx.cycle_id,
                        "version": idx,
                        "phase": exc.phase,
                    })
                    ctx.aborted = False
                    ctx.abort_reason = ""
                    state.transition(CycleState.REGENERATING,
                                     "rgo_fusion_divergence_retry", now_iso())
                    report.cycles.append(cycle)
                    continue

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
                    ctx.fusion = None
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
        report_context_eru = [
            c.get("eru_checkpoint") for c in report.cycles if c.get("eru_checkpoint")
        ]
        if report_context_eru:
            report.context_steps.append({
                "phase": "persistence",
                "module": "ERU_Engine",
                "ok": all(x.get("verified", False) for x in report_context_eru),
                "info": {"checkpoints": report_context_eru},
                "ts": now_iso(),
            })

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
        report.fusion = (
            {
                "cycle_id": ctx.fusion.cycle_id,
                "version": ctx.fusion.version,
                "target_hash": ctx.fusion.target_hash,
                "ara_hash": ctx.fusion.ara_hash,
                "etr_hash": ctx.fusion.etr_hash,
                "itr_hash": ctx.fusion.itr_hash,
                "eru_snapshot_hashes": dict(ctx.fusion.eru_snapshot_hashes),
                "fusion_snapshot_hash": ctx.fusion.fusion_snapshot_hash,
                "fused_hash": ctx.fusion.fused_hash,
                "integrity_ok": ctx.fusion.integrity_ok,
                "created_at": ctx.fusion.created_at,
            }
            if ctx.fusion is not None else None
        )
        er.artifacts["fusion_mirror"] = report.fusion
        report.execution_report = er.finalize().as_dict()
        self._history.append(report)
        return report

    def _collect_flaws(self, text: str) -> list[Any]:
        flaws = list(self._ara.detect(text))
        structural = getattr(self._ara, "detect_structural", lambda _t: [])(text)
        relational = getattr(self._ara, "detect_relational", lambda _t: [])(text)
        return flaws + list(relational) + list(structural)

    def _run_phases_canonical(self, ctx: CycleContext, cycle: dict, idx: int, pre_hash: str | None = None) -> None:
        self._phase_ingestion(ctx, cycle, idx)
        self._dispatch_emit_trace(ctx, CyclePhase.INGESTION)
        self._phase_audit(ctx, cycle)
        self._dispatch_emit_trace(ctx, CyclePhase.AUDIT)
        self._phase_regeneration(ctx, cycle)
        self._dispatch_emit_trace(ctx, CyclePhase.REGENERATION)
        self._phase_identity(ctx, cycle, idx)
        self._dispatch_emit_trace(ctx, CyclePhase.IDENTITY)
        etr_result = self._phase_ethics(ctx, cycle)
        self._dispatch_emit_trace(ctx, CyclePhase.ETHICS)
        strategy = self._phase_strategy(ctx, cycle, idx)
        self._dispatch_emit_trace(ctx, CyclePhase.STRATEGY)
        result = self._phase_execution(ctx, cycle, strategy)
        self._dispatch_emit_trace(ctx, CyclePhase.EXECUTION)
        self._phase_validation(ctx, cycle, etr_result)
        self._dispatch_emit_trace(ctx, CyclePhase.VALIDATION)
        self._synchronize_fusion(ctx, cycle, idx)
        self._phase_persistence(ctx, cycle, idx, result)
        self._dispatch_emit_trace(ctx, CyclePhase.PERSISTENCE)
        self._phase_snapshot(ctx, cycle, idx)
        self._dispatch_emit_trace(ctx, CyclePhase.SNAPSHOT)
        self._phase_monitoring(ctx, cycle)
        self._dispatch_emit_trace(ctx, CyclePhase.MONITORING)
        self._phase_governance(ctx, cycle)
        self._dispatch_emit_trace(ctx, CyclePhase.GOVERNANCE)

    def _phase_ingestion(self, ctx, cycle, idx):
        guard = self._dna.guard(f"cycle_{idx}", ctx.current)
        self._record(ctx, CyclePhase.INGESTION, "DNA_Tags", not guard.blocked,
                     tags=list(guard.tags), blocked=guard.blocked)
        cycle["phases"]["ingestion"] = {"blocked": guard.blocked, "tags": list(guard.tags)}
        if guard.blocked:
            raise _Aborted("INGESTION", "dna_block")

    def _phase_audit(self, ctx, cycle):
        lexical = list(self._ara.detect(ctx.current))
        semantic = list(getattr(self._ara, "detect_semantic", lambda _t: [])(ctx.current))
        structural = list(getattr(self._ara, "detect_structural", lambda _t: [])(ctx.current))
        relational = list(getattr(self._ara, "detect_relational", lambda _t: [])(ctx.current))
        cycle["_flaws"] = lexical + semantic + relational + structural
        if hasattr(self._ara, "analyze_semantics"):
            ctx.register_artifact("audit_semantic_fingerprint", self._ara.analyze_semantics(ctx.current).fingerprint)
        cycle["phases"]["audit"] = {
            "lexical": [f.kind for f in lexical],
            "semantic": [f.kind for f in semantic],
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
        structured = (
            self._identity.validate_structured(ctx.current)
            if hasattr(self._identity, "validate_structured")
            else {"approved": ident.identity_approved, "violations": ident.violations}
        )
        approved = ident.identity_approved and bool(structured.get("approved", True))
        cycle["phases"]["identity"] = {
            "approved": approved,
            "violations": list(ident.violations),
            "structured_approved": bool(structured.get("approved", True)),
            "structured_violations": list(structured.get("violations", ())),
            "semantic_fingerprint": structured.get("fingerprint"),
            "semantic_relations": structured.get("relations"),
        }
        ctx.register_artifact("identity_semantic_fingerprint", structured.get("fingerprint"))
        self._record(ctx, CyclePhase.IDENTITY, "IdentityCore", approved,
                     **cycle["phases"]["identity"])
        if not approved:
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
        try:
            if hasattr(self._itr, "generate_strategic"):
                strategy_context = {
                    "cycle": idx,
                    "ara_audit": {
                        "flaws": [getattr(f, "kind", str(f)) for f in cycle.get("_flaws", [])],
                        "semantic_fingerprint": ctx.artifacts.get("audit_semantic_fingerprint"),
                    },
                    "etr_approved": bool(cycle.get("phases", {}).get("ethics", {}).get("approved", False)),
                    "rgo_regeneration_inputs": list(ctx.flags.get("rgo_regeneration_inputs", [])),
                }
                strategy = self._itr.generate_strategic(ctx.current, strategy_context)
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
        except Exception as exc:
            cycle["phases"]["strategy"] = {
                "type": "failure",
                "error": f"{type(exc).__name__}: {exc}",
            }
            self._record(
                ctx,
                CyclePhase.STRATEGY,
                "ITR",
                False,
                **cycle["phases"]["strategy"],
            )
            raise _Aborted(
                "STRATEGY",
                f"itr_strategy_failure:{type(exc).__name__}:{exc}",
            ) from exc

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
        # "ok" já é o argumento posicional do registro; não o repassamos em **info.
        self._record(ctx, CyclePhase.EXECUTION, "ITR", ok, **info)
        if not ok:
            raise _Aborted("EXECUTION", "execution_rollback_triggered")
        return result

    def _phase_validation(self, ctx, cycle, etr_result):
        result = self._etr.validate(ctx.current, mode="default")
        semantic_validation = (
            self._etr.validate_semantic_frame(ctx.current)
            if hasattr(self._etr, "validate_semantic_frame")
            else {"ok": result.approved, "fingerprint": None}
        )
        filter_validation = (
            self._filters.evaluate_structured(ctx.current)
            if hasattr(self._filters, "evaluate_structured")
            else {"ok": True, "results": [], "failures": []}
        )
        approved = (
            result.approved
            and bool(semantic_validation.get("ok", True))
            and bool(filter_validation.get("ok", True))
        )
        cycle["phases"]["validation"] = {
            "approved": approved,
            "reason": result.reason,
            "previous_ethics_approved": etr_result.approved,
            "semantic_approved": bool(semantic_validation.get("ok", True)),
            "semantic_fingerprint": semantic_validation.get("fingerprint"),
            "semantic_findings": semantic_validation.get("findings", []),
            "filter_chain_ok": bool(filter_validation.get("ok", True)),
            "filter_chain_results": filter_validation.get("results", []),
            "filter_chain_failures": filter_validation.get("failures", []),
        }
        self._record(ctx, CyclePhase.VALIDATION, "ETR", approved,
                     **cycle["phases"]["validation"])
        if not approved:
            if not result.approved:
                reason = result.reason
            elif not semantic_validation.get("ok", True):
                reason = "semantic_validation_rejected"
            else:
                reason = "ethical_filter_chain_failure"
            raise _Aborted("VALIDATION", reason)

    def _synchronize_fusion(self, ctx, cycle, idx):
        """Sincroniza ARA/ETR/ITR/ERU no mesmo estado versionado do ciclo."""
        if self._trinity is None or not hasattr(self._trinity, "fuse_and_mirror"):
            return
        ara_phase = dict(cycle.get("phases", {}).get("audit", {}))
        etr_phase = dict(cycle.get("phases", {}).get("validation", {}))
        itr_phase = dict(cycle.get("phases", {}).get("execution", {}))
        mirror = self._trinity.fuse_and_mirror(
            cycle_id=ctx.cycle_id,
            target=ctx.current,
            version=idx,
            ara_output={
                "cycle_id": ctx.cycle_id,
                "version": idx,
                "input_hash": hash_json(ctx.input),
                "state_hash": hash_json(ara_phase),
                "flaws": cycle.get("phases", {}).get("audit", {}),
                "semantic_fingerprint": ctx.artifacts.get("audit_semantic_fingerprint"),
            },
            etr_output={
                "cycle_id": ctx.cycle_id,
                "version": idx,
                "state_hash": hash_json(etr_phase),
                "approved": bool(etr_phase.get("approved", False)),
                "semantic_approved": bool(etr_phase.get("semantic_approved", False)),
                "filter_chain_ok": bool(etr_phase.get("filter_chain_ok", False)),
            },
            itr_output={
                "cycle_id": ctx.cycle_id,
                "version": idx,
                "state_hash": hash_json(itr_phase),
                "rollback": bool(itr_phase.get("rollback_triggered", False)),
                "metrics": itr_phase.get("metrics", {}),
            },
        )
        if mirror.target != ctx.current or mirror.cycle_id != ctx.cycle_id or mirror.version != idx:
            ctx.flags.setdefault("rgo_regeneration_inputs", []).append({
                "type": "FUSION_DIVERGENCE",
                "cycle_id": ctx.cycle_id,
                "version": idx,
                "reason": "mirror_target_or_identity_mismatch",
            })
            raise _Aborted("VALIDATION", "fusion_integrity_failed")

        audit = self._trinity.audit_mirror(ctx.cycle_id, version=idx)
        if not audit.get("ok", False):
            ctx.flags.setdefault("rgo_regeneration_inputs", []).append({
                "type": "FUSION_DIVERGENCE",
                "cycle_id": ctx.cycle_id,
                "version": idx,
                "reason": audit,
            })
            raise _Aborted("VALIDATION", "fusion_integrity_failed")

        target_hash = hash_json(ctx.current)
        snapshot_hashes = tuple(sorted((mirror.eru.get("snapshot_hashes") or {}).items()))
        ctx.fusion = CycleFusionState(
            cycle_id=mirror.cycle_id,
            version=mirror.version,
            target_hash=target_hash,
            ara_hash=mirror.eru.get("ara_hash", ""),
            etr_hash=mirror.eru.get("etr_hash", ""),
            itr_hash=mirror.eru.get("itr_hash", ""),
            eru_snapshot_hashes=snapshot_hashes,
            fusion_snapshot_hash=mirror.eru.get("fusion_snapshot_hash"),
            fused_hash=mirror.fused_hash,
            integrity_ok=bool(audit.get("ok", False)),
        )
        ctx.register_artifact("fusion_mirror", {
            "cycle_id": mirror.cycle_id,
            "version": mirror.version,
            "fused_hash": mirror.fused_hash,
            "integrity_ok": mirror.integrity_ok,
            "eru": mirror.eru,
        })
        cycle["fusion"] = {
            "version": idx,
            "fused_hash": mirror.fused_hash,
            "integrity_ok": mirror.integrity_ok,
            "audit": audit,
        }

    def _phase_persistence(self, ctx, cycle, idx, result):
        rid = self._temporal.insert({
            "cycle_id": ctx.cycle_id, "iteration": idx,
            "input": ctx.input, "state": ctx.current,
            "execution": getattr(result, "metrics", {}),
            "fusion": cycle.get("fusion"),
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
            {
                "cycle_id": ctx.cycle_id,
                "iteration": idx,
                "state": ctx.current,
                "fusion": (
                    {
                        "version": ctx.fusion.version,
                        "fused_hash": ctx.fusion.fused_hash,
                        "integrity_ok": ctx.fusion.integrity_ok,
                    } if ctx.fusion is not None else None
                ),
            },
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
        meta = None
        if self._trinity is not None and hasattr(self._trinity, "assess"):
            meta = self._trinity.assess(ctx.current)
            cycle["phases"]["governance"] = {
                "pending_infrastructure": "not_executed",
                "trinity_assessment": meta,
            }
            self._record(
                ctx, CyclePhase.GOVERNANCE, "TrinitySynergy", True,
                trinity_assessment=meta,
            )
        else:
            cycle["phases"]["governance"] = {
                "pending_infrastructure": "not_executed",
            }
        self._record(ctx, CyclePhase.GOVERNANCE, "RegenerativeLoop", True,
                     pending_infrastructure="not_executed",
                     trinity_assessment_attached=meta is not None)
    
    def _dispatch_emit_trace(self, ctx: CycleContext, phase: CyclePhase) -> None:
        if self._registry is None:
            return

        # Primeiro executa a camada de conexão operacional. Ela trata módulos
        # não-nucleares e não duplica as operações do núcleo do loop.
        if self._connected_runtime is not None:
            actions = self._connected_runtime.dispatch_phase(ctx, phase)
            blocking = [
                a for a in actions
                if getattr(a, "blocking", False) and not a.ok
            ]
            if blocking:
                detail = "; ".join(
                    f"{a.module}:{a.operation}:{a.detail.get('error', 'failed')}"
                    for a in blocking
                )
                raise _Aborted(phase.value.upper(), f"connected_module_failure:{detail}")

        for registered in self._registry.modules_for_phase(phase):
            if (
                self._connected_runtime is not None
                and registered.name not in self._connected_runtime.CORE_HANDLED
            ):
                continue
            status = getattr(registered.instance, "STATUS", None)
            if status is not None and status.value == "PENDING_INFRASTRUCTURE":
                ctx.record(phase.value, registered.name, True,
                           skipped=True, reason="PENDING_INFRASTRUCTURE")
                continue
            emitter = getattr(registered.instance, "emit_trace", None)
            if emitter is None:
                continue
            try:
                emitter(_PhaseTraceProxy(ctx, phase))
            except Exception as exc:
                ctx.record(phase.value, registered.name, False, error=str(exc))

    @staticmethod
    def _record(ctx: CycleContext, phase: CyclePhase,
                module: str, ok: bool, **info: Any) -> None:
        """Registra evidência de uma etapa no contexto real do ciclo."""
        ctx.record(phase.value, module, ok, **info)

    def history(self) -> list[LoopReport]:
        return list(self._history)

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("regeneration", self.NAME, True, version=self.VERSION)
