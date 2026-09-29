from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import threading
from typing import Any, Callable

from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.vagus_bus import VagusNerveBus
from sara.meta.eru_engine import ERU_Engine
from sara.meta.eru_trinity_bridge import ERUTrinityBridge
from sara.core.trinity_eru_unified import TrinityERUUnified
from sara.omega.soul_services import MicroMacroManager
from sara.rgo.engine import RGOEngine


@dataclass(frozen=True)
class StageEnvelope:
    sequence_index: int
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
    rgo_evidence_chain_hash: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "sequence_index": self.sequence_index,
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
            "rgo_evidence_chain_hash": self.rgo_evidence_chain_hash,
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
    """Boundary processor for the existing TrinityERUUnified.

    RGO owns finding/evidence intake. TrinityERUUnified remains the execution
    authority for ARA/ITR/ETR/ERU. This class does not reproduce their algorithms;
    it binds their real observations into one ordered evidence stream and adds
    the existing MMD scale lens and Vagus/Horta integration boundary.
    """

    NAME = "RGOTrinityProcessor"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = (
        "RGOEngine",
        "TrinityERUUnified",
        "MicroMacroManager",
        "ERU_Engine",
        "ERUTrinityBridge",
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

    PHASE_SCALE = {
        "INPUT": "MICRO",
        "ARA": "MICRO",
        "ITR_PLAN": "MID",
        "ETR_PRE": "MID",
        "ARA_REGEN": "MID",
        "ETR_POST_REGEN": "MID",
        "ITR_EXEC": "MID",
        "ETR_POST_EXEC": "MID",
        "FINAL": "MACRO",
        "FINAL_RESULT": "MACRO",
    }

    def __init__(
        self,
        *,
        rgo: RGOEngine,
        trinity: TrinityERUUnified,
        mmd: MicroMacroManager,
        vagus_bus: VagusNerveBus,
        eru: ERU_Engine,
        eru_bridge: ERUTrinityBridge | None = None,
        horta_sink: Callable[[StageEnvelope], dict[str, Any] | None] | None = None,
    ) -> None:
        self._rgo = rgo
        self._trinity = trinity
        self._mmd = mmd
        self._vagus = vagus_bus
        self._eru = eru
        self._eru_bridge = eru_bridge or trinity.bridge()
        self._horta_sink = horta_sink
        self._lock = threading.RLock()
        self._last: TrinityProcessorResult | None = None

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [phase.value for phase in self.CYCLE_PHASES],
            "topology": "composite_processor_over_existing_trinity",
            "execution_authority": "TrinityERUUnified",
            "stage_order": [
                "RGO",
                "existing-Trinity-observations",
                "ERU",
                "MMD",
            ],
            "inheritance": "ordered_content_hash_chain",
            "rgo_stage_evidence": True,
            "vagus_bus": True,
            "horta_sink_configured": self._horta_sink is not None,
            "mmd_reused_existing_instance": True,
            "eru_bridge_reused_existing_instance": True,
        }

    @staticmethod
    def _hash(value: Any) -> str:
        raw = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    def _emit(self, event_type: str, stage: StageEnvelope) -> None:
        try:
            result = self._vagus.publish(
                source=self.NAME,
                target="SARA",
                event_type=event_type,
                payload=stage.as_dict(),
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
        scale: str | None = None,
        status: str = "OBSERVED",
        eru_snapshot_hash: str | None = None,
    ) -> StageEnvelope:
        payload_hash = self._hash(data)
        sequence_index = (parent.sequence_index + 1) if parent else 1
        effective_scale = scale or self.PHASE_SCALE.get(stage, "MID")

        self._mmd.transition_explicit(
            effective_scale,
            evidence={
                "finding_id": finding_id,
                "cycle_id": cycle_id,
                "stage": stage,
                "sequence_index": sequence_index,
                "parent_hash": parent.output_hash if parent else "GENESIS",
                "output_hash": payload_hash,
            },
        )

        snapshot_hash = eru_snapshot_hash
        if snapshot_hash is None:
            observation = self._eru_bridge.observe(cycle_id, stage, data)
            snapshot_hash = observation.snapshot_hash

        envelope = StageEnvelope(
            sequence_index=sequence_index,
            stage=stage,
            scale=effective_scale,
            finding_id=finding_id,
            cycle_id=cycle_id,
            parent_stage=parent.stage if parent else None,
            parent_hash=parent.output_hash if parent else "GENESIS",
            input_hash=parent.output_hash if parent else self._hash({"finding_id": finding_id}),
            output_hash=payload_hash,
            status=status,
            eru_snapshot_hash=snapshot_hash,
            data=data,
        )

        evidence_record = self._rgo.record_stage_evidence(
            finding_id=finding_id,
            cycle_id=cycle_id,
            sequence_index=envelope.sequence_index,
            stage=stage,
            parent_hash=envelope.parent_hash,
            output_hash=envelope.output_hash,
            status=status,
        )

        envelope = StageEnvelope(
            sequence_index=envelope.sequence_index,
            stage=envelope.stage,
            scale=envelope.scale,
            finding_id=envelope.finding_id,
            cycle_id=envelope.cycle_id,
            parent_stage=envelope.parent_stage,
            parent_hash=envelope.parent_hash,
            input_hash=envelope.input_hash,
            output_hash=envelope.output_hash,
            status=envelope.status,
            eru_snapshot_hash=envelope.eru_snapshot_hash,
            data=envelope.data,
            rgo_evidence_chain_hash=evidence_record["chain_hash"],
        )

        self._emit("RGO_TRINITY_STAGE", envelope)
        self._persist_horta(envelope)
        return envelope

    @staticmethod
    def _status_from_observation(phase: str, data: Any) -> str:
        if isinstance(data, dict):
            if phase == "FINAL_RESULT" and data.get("converged") is False:
                return "INCONCLUSIVE"
            if data.get("approved") is False:
                return "BLOCKED"
            if data.get("rollback") is True:
                return "BLOCKED"
        return "OBSERVED"

    def process(
        self,
        payload: dict[str, Any],
        *,
        cycle_id: str | None = None,
    ) -> TrinityProcessorResult:
        with self._lock:
            cycle_id = cycle_id or self._hash(payload)[7:19]
            env = self._rgo.prepare(payload)
            rgo_record = self._rgo.ingest_envelope(env)

            rgo_stage = self._stage(
                stage="RGO",
                finding_id=env.finding_id,
                cycle_id=cycle_id,
                parent=None,
                data={
                    "dual_status": env.dual_status.value,
                    "dual_property": env.dual_property,
                    "verification_state": env.verification_state.value,
                    "evidence_ids": [e.id for e in env.evidence],
                    "canonical_hash": rgo_record["canonical_hash"],
                },
                scale="MICRO",
                status="INGESTED",
            )

            bridge = self._trinity.bridge()
            before_ids = set(bridge.observed_cycle_ids())

            # Existing TrinityERUUnified is the sole execution path for
            # ARA/ITR/ETR/ERU. No duplicate implementation is performed here.
            unified_report = self._trinity.apply_to(env.failure_description)

            after_ids = bridge.observed_cycle_ids()
            new_cycle_ids = [cid for cid in after_ids if cid not in before_ids]

            stages: list[StageEnvelope] = [rgo_stage]
            parent = rgo_stage

            observation_count = 0
            for trinity_cycle_id in new_cycle_ids:
                audit = bridge.audit_cycle(trinity_cycle_id)
                for observation in audit.get("observations", []):
                    phase = str(observation.get("phase", ""))
                    snapshot_name = str(observation.get("snapshot_name", ""))
                    if not phase or not snapshot_name:
                        continue
                    state = self._eru.snapshot_state(snapshot_name)
                    stage_data = {
                        "trinity_cycle_id": trinity_cycle_id,
                        "phase": phase,
                        "snapshot_name": snapshot_name,
                        "snapshot_hash": observation.get("snapshot_hash"),
                        "state": state,
                    }
                    stage = self._stage(
                        stage=f"TRINITY::{phase}",
                        finding_id=env.finding_id,
                        cycle_id=cycle_id,
                        parent=parent,
                        data=stage_data,
                        scale=self.PHASE_SCALE.get(phase, "MID"),
                        status=self._status_from_observation(phase, state),
                        eru_snapshot_hash=str(observation.get("snapshot_hash") or ""),
                    )
                    stages.append(stage)
                    parent = stage
                    observation_count += 1

            final_report = unified_report.trinity_report
            eru_stage = self._stage(
                stage="ERU",
                finding_id=env.finding_id,
                cycle_id=cycle_id,
                parent=parent,
                data={
                    "execution_authority": "TrinityERUUnified",
                    "new_trinity_cycle_ids": new_cycle_ids,
                    "observed_stage_count": observation_count,
                    "trinity_converged": final_report.converged,
                    "total_iterations": final_report.total_iterations,
                    "final_text_hash": self._hash(final_report.final_text),
                },
                scale="MACRO",
                status="FINALIZED" if final_report.converged else "INCONCLUSIVE",
            )
            stages.append(eru_stage)
            parent = eru_stage

            mmd_stage = self._stage(
                stage="MMD",
                finding_id=env.finding_id,
                cycle_id=cycle_id,
                parent=parent,
                data={
                    "state": self._mmd.state,
                    "observation_count": len(self._mmd._observations),
                    "trinity_converged": final_report.converged,
                    "scale_policy": "explicit_evidence",
                },
                scale="MACRO",
                status="OBSERVED",
            )
            stages.append(mmd_stage)

            final_status = "VALIDATED" if final_report.converged else "INCONCLUSIVE"
            self._last = TrinityProcessorResult(
                cycle_id=cycle_id,
                finding_id=env.finding_id,
                stages=tuple(stages),
                final_status=final_status,
                final_output_hash=mmd_stage.output_hash,
                mmd_state=self._mmd.state,
                rgo_record=rgo_record,
            )
            return self._last

    def last_result(self) -> TrinityProcessorResult | None:
        return self._last
