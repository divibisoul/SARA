from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import json


SCHEMA_VERSION = "1.0.0"


class VerificationState(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    INCONCLUSIVE = "INCONCLUSIVE"


class EpistemicMode(str, Enum):
    EXECUTION = "EXECUTION"
    INSPECTION = "INSPECTION"
    INFERENCE = "INFERENCE"
    EXTERNAL = "EXTERNAL"


class ActionabilityStatus(str, Enum):
    ACTIONABLE = "ACTIONABLE"
    NON_ACTIONABLE = "NON_ACTIONABLE"
    INFORMATIONAL = "INFORMATIONAL"
    DUPLICATE = "DUPLICATE"
    INCONCLUSIVE = "INCONCLUSIVE"
    UNDEFINED = "UNDEFINED"


class DualStatus(str, Enum):
    DERIVED_FROM_CONTRACT = "DERIVED_FROM_CONTRACT"
    UNRESOLVED = "UNRESOLVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CapabilityState(str, Enum):
    DERIVED = "DERIVED"
    IMPLEMENTED = "IMPLEMENTED"
    TESTED = "TESTED"
    VALIDATED = "VALIDATED"
    PROMOTABLE = "PROMOTABLE"
    PROMOTED = "PROMOTED"


class RGOValidationError(ValueError):
    pass


@dataclass(frozen=True)
class EvidenceRef:
    id: str
    kind: str
    ref: str


@dataclass(frozen=True)
class RGOEnvelope:
    finding_id: str
    object_id: str
    timestamp: str
    correlation_id: str
    trace_id: str
    source_system: str
    source_module: str
    source_version: str
    epistemic_mode: EpistemicMode
    verification_state: VerificationState
    actionability: ActionabilityStatus
    failure_type: str
    failure_description: str
    failure_nature: str
    correction_problem: str
    required_property: str
    dual_status: DualStatus
    dual_property: str
    evidence: tuple[EvidenceRef, ...] = ()
    dual_evidence_refs: tuple[str, ...] = ()
    capability_id: str = ""
    capability_state: CapabilityState | None = None
    provenance_origin: str = ""
    parent_ids: tuple[str, ...] = ()
    input_hash: str = ""
    actionability_reason: str = ""
    failure_cause: str = ""
    failure_impact: str = ""
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, value: dict) -> "RGOEnvelope":
        if not isinstance(value, dict):
            raise RGOValidationError("RGO_ENVELOPE_OBJECT_REQUIRED")
        source = value.get("source") or {}
        epistemic = value.get("epistemic") or {}
        actionability = value.get("actionability") or {}
        failure = value.get("failure") or {}
        boundary = value.get("correction_boundary") or {}
        dual = value.get("dual") or {}
        capability = value.get("capability") or {}
        prov = value.get("provenance") or {}
        evidence = tuple(
            EvidenceRef(str(x.get("id", "")), str(x.get("kind", "")), str(x.get("ref", "")))
            for x in (value.get("evidence") or [])
            if isinstance(x, dict)
        )
        try:
            epistemic_mode = EpistemicMode(str(epistemic.get("mode", "")))
            verification_state = VerificationState(str(epistemic.get("verification_state", "")))
            actionability_status = ActionabilityStatus(str(actionability.get("status", "")))
            dual_status = DualStatus(str(dual.get("status", "UNRESOLVED")))
            capability_state = CapabilityState(str(capability["state"])) if capability.get("state") else None
        except ValueError as exc:
            raise RGOValidationError("RGO_ENUM_INVALID") from exc

        env = cls(
            finding_id=str(value.get("finding_id", "")),
            object_id=str(value.get("object_id", "")),
            timestamp=str(value.get("timestamp", "")),
            correlation_id=str(value.get("correlation_id", "")),
            trace_id=str(value.get("trace_id", "")),
            source_system=str(source.get("system", "")),
            source_module=str(source.get("module", "")),
            source_version=str(source.get("version", "")),
            epistemic_mode=epistemic_mode,
            verification_state=verification_state,
            actionability=actionability_status,
                        failure_type=str(failure.get("type", "")),
            failure_description=str(failure.get("description", "")),
            failure_nature=str(failure.get("nature", "")),
            correction_problem=str(boundary.get("problem_to_resolve", "")),
            required_property=str(boundary.get("required_property", "")),
            dual_status=dual_status,
            dual_property=str(dual.get("property", "")),
            evidence=evidence,
            dual_evidence_refs=tuple(str(x) for x in (dual.get("evidence_refs") or [])),
            capability_id=str(capability.get("id", "")),
            capability_state=capability_state,
            provenance_origin=str(prov.get("origin", "")),
            parent_ids=tuple(str(x) for x in (prov.get("parent_ids") or [])),
            input_hash=str(prov.get("input_hash", "")),
            actionability_reason=str(actionability.get("reason", "")),
            failure_cause=str(failure.get("cause", "")),
            failure_impact=str(failure.get("impact", "")),
            schema_version=str(value.get("schema_version", "")),
        )
        env.validate()
        return env

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise RGOValidationError("RGO_SCHEMA_VERSION_UNSUPPORTED")
        if not self.finding_id or not self.object_id:
            raise RGOValidationError("RGO_ID_REQUIRED")
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise RGOValidationError("RGO_TIMESTAMP_INVALID") from exc
        if not self.correlation_id or not self.trace_id:
            raise RGOValidationError("RGO_CORRELATION_TRACE_REQUIRED")
        if not self.source_system or not self.source_module or not self.source_version:
            raise RGOValidationError("RGO_SOURCE_REQUIRED")
        if not self.failure_type or not self.failure_description or not self.failure_nature:
            raise RGOValidationError("RGO_FAILURE_REQUIRED")
        if self.dual_status == DualStatus.DERIVED_FROM_CONTRACT:
            if not self.correction_problem or not self.required_property or not self.dual_property:
                raise RGOValidationError("RGO_DUAL_DERIVATION_REQUIRED")
        if not self.evidence:
            raise RGOValidationError("RGO_EVIDENCE_REQUIRED")
        for ref in self.evidence:
            if not ref.id or not ref.kind or not ref.ref:
                raise RGOValidationError("RGO_EVIDENCE_REF_INVALID")
        if not self.provenance_origin or not self.input_hash:
            raise RGOValidationError("RGO_PROVENANCE_REQUIRED")

    def with_derived_dual(self) -> "RGOEnvelope":
        if not self.correction_problem or not self.required_property:
            return RGOEnvelope(**{**self.__dict__, "dual_status": DualStatus.UNRESOLVED, "dual_property": "", "dual_evidence_refs": ()})
        return RGOEnvelope(
            **{
                **self.__dict__,
                "dual_status": DualStatus.DERIVED_FROM_CONTRACT,
                "dual_property": self.required_property,
                "dual_evidence_refs": tuple(ref.id for ref in self.evidence),
            }
        )

    def canonical_hash(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "finding_id": self.finding_id,
            "object_id": self.object_id,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "source": {"system": self.source_system, "module": self.source_module, "version": self.source_version},
            "epistemic": {"mode": self.epistemic_mode.value, "verification_state": self.verification_state.value},
            "actionability": {"status": self.actionability.value, "reason": self.actionability_reason},
            "failure": {"type": self.failure_type, "description": self.failure_description, "nature": self.failure_nature, "cause": self.failure_cause, "impact": self.failure_impact},
            "correction_boundary": {"problem_to_resolve": self.correction_problem, "required_property": self.required_property},
            "dual": {"status": self.dual_status.value, "property": self.dual_property, "evidence_refs": list(self.dual_evidence_refs)},
            "capability": {"id": self.capability_id, "state": self.capability_state.value if self.capability_state else ""},
            "evidence": [{"id": x.id, "kind": x.kind, "ref": x.ref} for x in self.evidence],
            "provenance": {"origin": self.provenance_origin, "parent_ids": list(self.parent_ids), "input_hash": self.input_hash},
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()
