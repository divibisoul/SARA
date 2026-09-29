from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable

from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.core.ara_extended import ARA_Extended
from sara.core.etr_extended import ETR_Extended
from sara.core.itr_extended import ITR_Extended
from sara.meta.eru_engine import ERU_Engine
from sara.rgo.engine import RGOEngine
from sara.omega.soul_services import MicroMacroManager
from sara.infra.vagus_bus import VagusNerveBus


@dataclass(frozen=True)
class StageEnvelope:
    stage: str
    scale: str
    finding_id: str
    cycle_id: str
    parent_stage: str | None
    parent_hash: str
    input_hash: str
    output_hash: str
    status: str
    eru_snapshot_hash: str
    data: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "scale": self.scale,
            "finding_id": self.finding_id,
            "cycle_id": self.cycle_id,
            "parent_stage": self.parent_stage,
            "parent_hash": self.parent_hash,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "status": self.status,
            "eru_snapshot_hash": self.eru_snapshot_hash,
            "data": self.data,
        }


@dataclass(frozen=True)
class TrinityProcessorResult:
    cycle_id: str
    finding_id: str
    stages: tuple[StageEnvelope, ...]
    final_status: str
    final_output_hash: str
    mmd_state: str
    rgo_record: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "finding_id": self.finding_id,
            "stages": [stage.as_dict() for stage in self.stages],
            "final_status": self.final_status,
            "final_output_hash": self.final_output_hash,
            "mmd_state": self.mmd_state,
            "rgo_record": dict(self.rgo_record),
        }


class RGOTrinityProcessor:
    """Composto RGO → ARA → ITR → ETR → ERU com MMD e Vagus.

    Não cria uma segunda autoridade. Cada estágio recebe a saída do anterior
    por hash de conteúdo; ERU preserva os estágios como snapshots históricos.
    MMD fornece a lente de escala explicitamente registrada, não uma política
    implícita de parada.
    """

    NAME = "RGOTrinityProcessor"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = (
        "RGOEngine", "ARA_Extended", "ITR_Extended",
        "ETR_Extended", "ERU_Engine", "MicroMacroManager",
    )
    CYCLE_PHASES = (
        CyclePhase.INGESTION,
        CyclePhase.AUDIT,
        CyclePhase.STRATEGY,
        CyclePhase.ETHICS,
        CyclePhase.REGENERATION,
        CyclePhase.EXECUTION,
        CyclePhase.PERSISTENCE,
        CyclePhase.MONITORING,
    )
    STAGE_SCALE = {
        "RGO": "MICRO",
        "ARA": "MICRO",
        "ITR": "MID",
        "ETR": "MID",
        "ERU": "MACRO",
        "MMD": "MACRO",
    }

    def __init__(
        self,
        *,
        rgo: RGOEngine,
        ara: ARA_Extended,
        itr: ITR_Extended,
        etr: ETR_Extended,
        eru: ERU_Engine,
        mmd: MicroMacroManager,
        vagus_bus: VagusNerveBus,
        horta_sink: Callable[[StageEnvelope], dict[str, Any] | None] | None = None,
    ) -> None:
        self._rgo = rgo
        self._ara = ara
        self._itr = itr
        self._etr = etr
        self._eru = eru
        self._mmd = mmd
        self._vagus = vagus_bus
        self._horta_sink = horta_sink
        self._last: TrinityProcessorResult | None = None

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [phase.value for phase in self.CYCLE_PHASES],
            "topology": "composite_multi_core",
            "stage_order": ["RGO", "ARA", "ITR", "ETR", "ERU", "MMD"],
            "inheritance": "content_hash_chain",
            "vagus_bus": True,
            "horta_sink_configured": self._horta_sink is not None,
        }

    @staticmethod
    def _hash(value: Any) -> str:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    def _emit(self, event_type: str, stage: StageEnvelope) -> None:
        payload = stage.as_dict()
        try:
            result = self._vagus.publish(
                source=self.NAME,
                target="SARA",
                event_type=event_type,
                payload=payload,
                status="OBSERVE",
            )
            import asyncio
            if asyncio.iscoroutine(result):
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    asyncio.run(result)
                else:
                    asyncio.create_task(result)
        except Exception:
            # Failure to publish telemetry must not fabricate or rewrite stage history.
            return

    def _persist_horta(self, stage: StageEnvelope) -> dict[str, Any] | None:
        if self._horta_sink is None:
            return None
        return self._horta_sink(stage)

    def _stage(
        self,
        *,
        stage: str,
        finding_id: str,
        cycle_id: str,
        parent: StageEnvelope | None,
        data: dict[str, Any],
        status: str = "EXECUTED",
    ) -> StageEnvelope:
        payload_hash = self._hash(data)
        envelope = StageEnvelope(
            stage=stage,
            scale=self.STAGE_SCALE[stage],
            finding_id=finding_id,
            cycle_id=cycle_id,
            parent_stage=parent.stage if parent else None,
            parent_hash=parent.output_hash if parent else "GENESIS",
            input_hash=parent.output_hash if parent else self._hash({"finding_id": finding_id}),
            output_hash=payload_hash,
            status=status,
            eru_snapshot_hash=self._eru.freeze(
                f"RGO_TRINITY_STAGE::{cycle_id}::{len(self._eru._snapshots)}::{stage}",
                {
                    "stage": stage,
                    "finding_id": finding_id,
                    "cycle_id": cycle_id,
                    "parent_hash": parent.output_hash if parent else "GENESIS",
                    "output_hash": payload_hash,
                    "status": status,
                    "data": data,
                },
            ),
            data=data,
        )
        self._emit("RGO_TRINITY_STAGE", envelope)
        self._persist_horta(envelope)
        return envelope

    def process(self, payload: dict[str, Any], *, cycle_id: str | None = None) -> TrinityProcessorResult:
        cycle_id = cycle_id or self._hash(payload)[7:19]
        env = self._rgo.prepare(payload)
        rgo_record = self._rgo.ingest_envelope(env)

        parent: StageEnvelope | None = None
        stages: list[StageEnvelope] = []

        self._mmd.transition_explicit("MICRO", evidence={"stage": "RGO", "finding_id": env.finding_id})
        rgo_stage = self._stage(
            stage="RGO", finding_id=env.finding_id, cycle_id=cycle_id, parent=None,
            data={
                "dual_status": env.dual_status.value,
                "dual_property": env.dual_property,
                "verification_state": env.verification_state.value,
                "evidence_ids": [e.id for e in env.evidence],
            },
        )
        stages.append(rgo_stage)
        parent = rgo_stage

        text = env.failure_description
        lexical = self._ara.detect(text)
        semantic = self._ara.detect_semantic(text)
        structural = self._ara.detect_structural(text)
        relational = self._ara.detect_relational(text)
        ara_data = {
            "text": text,
            "lexical": [f.kind for f in lexical],
            "semantic": [f.kind for f in semantic],
            "structural": [f.kind for f in structural],
            "relational": [f.kind for f in relational],
            "semantic_fingerprint": self._ara.analyze_semantics(text).fingerprint,
            "finding_id": env.finding_id,
        }
        ara_stage = self._stage(stage="ARA", finding_id=env.finding_id, cycle_id=cycle_id, parent=parent, data=ara_data)
        stages.append(ara_stage)
        parent = ara_stage

        self._mmd.transition_explicit("MID", evidence={"stage": "ITR", "finding_id": env.finding_id, "parent_hash": parent.output_hash})
        plan = self._itr.generate_strategic(
            text,
            context={
                "ara_audit": ara_data,
                "rgo_dual_status": env.dual_status.value,
                "rgo_dual_property": env.dual_property,
            },
        )
        itr_data = {
            "objective": plan.objective,
            "phases": list(plan.phases),
            "criteria": list(plan.convergence_criteria),
            "rollback_points": list(plan.rollback_points),
        }
        itr_stage = self._stage(stage="ITR", finding_id=env.finding_id, cycle_id=cycle_id, parent=parent, data=itr_data)
        stages.append(itr_stage)
        parent = itr_stage

        pre_etr = self._etr.validate_multi_framework(
            f"{plan.objective} | phases={len(plan.phases)} | criteria={plan.convergence_criteria}"
        )
        etr_data = {
            "approved": pre_etr.approved,
            "consensus": pre_etr.consensus_score,
            "dissenting": list(pre_etr.dissenting_frameworks),
            "assessments": [a.__dict__ for a in pre_etr.assessments],
        }
        etr_stage = self._stage(stage="ETR", finding_id=env.finding_id, cycle_id=cycle_id, parent=parent, data=etr_data, status="VALIDATED" if pre_etr.approved else "BLOCKED")
        stages.append(etr_stage)
        parent = etr_stage
        if not pre_etr.approved:
            self._mmd.transition_explicit("MID", evidence={"stage": "ETR", "finding_id": env.finding_id, "approved": False})
            self._last = TrinityProcessorResult(cycle_id, env.finding_id, tuple(stages), "BLOCKED", parent.output_hash, self._mmd.state, rgo_record)
            return self._last

        regenerated = self._ara.regenerate_semantic(text, lexical + semantic + structural + relational)
        regen_data = {
            "transformed": regenerated.transformed,
            "plan_steps": list(regenerated.plan_steps),
            "integrity_hash": regenerated.integrity_hash,
            "preserved_length": regenerated.preserved_length,
        }
        regen_stage = self._stage(stage="ARA", finding_id=env.finding_id, cycle_id=cycle_id, parent=parent, data=regen_data)
        stages.append(regen_stage)
        parent = regen_stage

        post_etr = self._etr.validate_multi_framework(regenerated.transformed)
        post_data = {
            "approved": post_etr.approved,
            "consensus": post_etr.consensus_score,
            "dissenting": list(post_etr.dissenting_frameworks),
        }
        post_stage = self._stage(stage="ETR", finding_id=env.finding_id, cycle_id=cycle_id, parent=parent, data=post_data, status="VALIDATED" if post_etr.approved else "BLOCKED")
        stages.append(post_stage)
        parent = post_stage
        if not post_etr.approved:
            self._last = TrinityProcessorResult(cycle_id, env.finding_id, tuple(stages), "BLOCKED", parent.output_hash, self._mmd.state, rgo_record)
            return self._last

        result = self._itr.execute_composed(plan, initial_text=regenerated.transformed)
        exec_data = {
            "transformed": result.transformed,
            "rollback_triggered": result.rollback_triggered,
            "metrics": dict(result.metrics),
        }
        exec_stage = self._stage(stage="ITR", finding_id=env.finding_id, cycle_id=cycle_id, parent=parent, data=exec_data, status="EXECUTED" if not result.rollback_triggered else "BLOCKED")
        stages.append(exec_stage)
        parent = exec_stage
        if result.rollback_triggered:
            self._last = TrinityProcessorResult(cycle_id, env.finding_id, tuple(stages), "BLOCKED", parent.output_hash, self._mmd.state, rgo_record)
            return self._last

        final_etr = self._etr.validate_multi_framework(result.transformed)
        final_etr_data = {
            "approved": final_etr.approved,
            "consensus": final_etr.consensus_score,
            "dissenting": list(final_etr.dissenting_frameworks),
        }
        final_etr_stage = self._stage(stage="ETR", finding_id=env.finding_id, cycle_id=cycle_id, parent=parent, data=final_etr_data, status="VALIDATED" if final_etr.approved else "BLOCKED")
        stages.append(final_etr_stage)
        parent = final_etr_stage
        if not final_etr.approved:
            self._last = TrinityProcessorResult(cycle_id, env.finding_id, tuple(stages), "BLOCKED", parent.output_hash, self._mmd.state, rgo_record)
            return self._last

        self._mmd.transition_explicit("MACRO", evidence={"stage": "ERU", "finding_id": env.finding_id, "parent_hash": parent.output_hash})
        eru_hash = self._eru.freeze(
            f"RGO_TRINITY::{cycle_id}",
            {
                "finding_id": env.finding_id,
                "parent_hash": parent.output_hash,
                "stages": [stage.as_dict() for stage in stages],
            },
        )
        eru_data = {
            "snapshot": f"RGO_TRINITY::{cycle_id}",
            "snapshot_hash": eru_hash,
            "stage_count": len(stages),
        }
        eru_stage = self._stage(stage="ERU", finding_id=env.finding_id, cycle_id=cycle_id, parent=parent, data=eru_data, status="SNAPSHOTTED")
        stages.append(eru_stage)
        parent = eru_stage

        mmd_data = self._mmd.observe_scale(
            "MACRO",
            evidence={
                "stage_count": len(stages),
                "final_etr_approved": final_etr.approved,
                "eru_snapshot_hash": eru_hash,
            },
        )
        mmd_stage = self._stage(stage="MMD", finding_id=env.finding_id, cycle_id=cycle_id, parent=parent, data=mmd_data, status="OBSERVED")
        stages.append(mmd_stage)
        self._last = TrinityProcessorResult(
            cycle_id=cycle_id,
            finding_id=env.finding_id,
            stages=tuple(stages),
            final_status="VALIDATED",
            final_output_hash=mmd_stage.output_hash,
            mmd_state=self._mmd.state,
            rgo_record=rgo_record,
        )
        return self._last

    def last_result(self) -> TrinityProcessorResult | None:
        return self._last
