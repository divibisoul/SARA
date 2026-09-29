from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Any

from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.hashing import chain_hash
from sara.rgo.contracts import RGOEnvelope, RGOValidationError, DualStatus
from sara.core.provenance import Provenance


@dataclass(frozen=True)
class RGOState:
    accepted: int
    rejected: int
    last_hash: str
    integrity: bool


class RGOEngine:
    NAME = "RGOEngine"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = ("ProvenanceTracker",)
    CYCLE_PHASES = (CyclePhase.GOVERNANCE, CyclePhase.PERSISTENCE, CyclePhase.MONITORING)

    def __init__(self, *, provenance: Any, vagus_bus: Any | None = None) -> None:
        self._provenance = provenance
        self._vagus_bus = vagus_bus
        self._records: list[dict[str, Any]] = []
        self._chain: list[str] = []
        self._accepted = 0
        self._rejected = 0
        self._lock = threading.RLock()

    def describe(self) -> dict[str, Any]:
        state = self.state()
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [phase.value for phase in self.CYCLE_PHASES],
            "accepted": state.accepted,
            "rejected": state.rejected,
            "integrity": state.integrity,
            "last_hash": state.last_hash,
        }

    def emit_trace(self, ctx: Any) -> None:
        if hasattr(ctx, "record"):
            state = self.state()
            ctx.record(
                "monitoring",
                self.NAME,
                state.integrity,
                accepted=state.accepted,
                rejected=state.rejected,
                last_hash=state.last_hash,
            )

    def prepare(self, payload: dict[str, Any]) -> RGOEnvelope:
        return RGOEnvelope.from_dict(payload).with_derived_dual()

    def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            env = self.prepare(payload)
        except Exception:
            with self._lock:
                self._rejected += 1
            raise
        return self.ingest_envelope(env)

    def ingest_envelope(self, env: RGOEnvelope) -> dict[str, Any]:
        try:
            env = env.with_derived_dual()
            digest = env.canonical_hash()
            self._provenance.register(
                entity=f"RGO:{env.finding_id}",
                provenance=Provenance.INFERRED if env.epistemic_mode.value == "INFERENCE" else Provenance.HISTORICAL,
                evidence=digest,
                source=env.provenance_origin,
            )
        except Exception:
            with self._lock:
                self._rejected += 1
            raise

        with self._lock:
            previous = self._chain[-1] if self._chain else "GENESIS"
            chain_value = chain_hash(
                previous,
                {"finding_hash": digest, "finding_id": env.finding_id},
            )
            record = {
                "finding_id": env.finding_id,
                "object_id": env.object_id,
                "canonical_hash": digest,
                "chain_hash": chain_value,
                "dual_status": env.dual_status.value,
                "dual_property": env.dual_property,
                "actionability": env.actionability.value,
                "verification_state": env.verification_state.value,
            }
            self._records.append(record)
            self._chain.append(chain_value)
            self._accepted += 1

        if self._vagus_bus is not None:
            try:
                self._publish_vagus(env, digest)
            except Exception:
                pass

        return {
            "status": "ACCEPTED",
            "finding_id": env.finding_id,
            "dual": {
                "status": env.dual_status.value,
                "property": env.dual_property,
            },
            "canonical_hash": digest,
            "history_index": len(self._records) - 1,
            "re_audit_required": True,
        }

    def _publish_vagus(self, env: RGOEnvelope, digest: str) -> None:
        import asyncio
        result = self._vagus_bus.publish(
            source=self.NAME,
            target="SARA",
            event_type="RGO_FINDING_RECEIVED",
            payload={
                "finding_id": env.finding_id,
                "object_id": env.object_id,
                "canonical_hash": digest,
                "dual_status": env.dual_status.value,
                "correlation_id": env.correlation_id,
                "trace_id": env.trace_id,
            },
            status="OBSERVE",
        )
        if asyncio.iscoroutine(result):
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(result)
            else:
                asyncio.create_task(result)

    def state(self) -> RGOState:
        with self._lock:
            previous = "GENESIS"
            ok = len(self._records) == len(self._chain)
            for record, chain_value in zip(self._records, self._chain):
                expected = chain_hash(previous, {"finding_hash": record["canonical_hash"], "finding_id": record["finding_id"]})
                if expected != chain_value or record["chain_hash"] != chain_value:
                    ok = False
                    break
                previous = chain_value
            return RGOState(self._accepted, self._rejected, self._chain[-1] if self._chain else "GENESIS", ok)
