from __future__ import annotations

from datetime import datetime

from sara.rgo.contracts import (
    ActionabilityStatus,
    DualStatus,
    EpistemicMode,
    RGOEnvelope,
    RGOValidationError,
    VerificationState,
    EvidenceRef,
)


def from_bugshield(payload: dict) -> RGOEnvelope:
    schema = str(payload.get("schema_version", ""))
    if not (schema.startswith("1.1.") or schema.startswith("1.2.")):
        raise RGOValidationError(f"BUGSHIELD_SCHEMA_UNSUPPORTED:{schema}")

    scan_id = str(payload.get("scan_id", ""))
    timestamp = str(payload.get("timestamp", ""))
    scanner = payload.get("scanner") or {}
    scope = payload.get("scope") or {}
    finding = payload.get("finding") or {}
    if not isinstance(scanner, dict) or not isinstance(scope, dict) or not isinstance(finding, dict):
        raise RGOValidationError("BUGSHIELD_REQUIRED_SECTION_INVALID")
    input_hash = str(scope.get("input_hash", ""))
    finding_id = str(finding.get("id", ""))
    description = str(finding.get("description", ""))
    finding_type = str(finding.get("type", ""))
    category = str(finding.get("category", ""))
    mode = str(finding.get("epistemic_mode", ""))
    verification = str(finding.get("verification_state", ""))
    if not scan_id or not timestamp or not input_hash:
        raise RGOValidationError("BUGSHIELD_IDENTITY_REQUIRED")
    if not finding_id or not description or not finding_type or not category or not mode or not verification:
        raise RGOValidationError("BUGSHIELD_FINDING_REQUIRED")
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        epistemic_mode = EpistemicMode(mode)
        verification_state = VerificationState(verification)
    except (ValueError, TypeError) as exc:
        raise RGOValidationError("BUGSHIELD_METADATA_INVALID") from exc

    raw_evidence = finding.get("evidence") or []
    evidence = tuple(
        EvidenceRef(str(row.get("id", "")), str(row.get("kind", "")), str(row.get("ref", "")))
        for row in raw_evidence if isinstance(row, dict)
    )
    if not evidence or any(not (x.id and x.kind and x.ref) for x in evidence):
        raise RGOValidationError("BUGSHIELD_EVIDENCE_REQUIRED")

    boundary = finding.get("correction_boundary") or {}
    if not isinstance(boundary, dict):
        boundary = {}

    env = RGOEnvelope(
        finding_id=finding_id,
        object_id=input_hash,
        timestamp=timestamp,
        correlation_id=scan_id,
        trace_id=f"{scan_id}:{finding_id}",
        source_system=str(scanner.get("name", "")),
        source_module="BugShield",
        source_version=str(scanner.get("version", "")),
        epistemic_mode=epistemic_mode,
        verification_state=verification_state,
        actionability=ActionabilityStatus.UNDEFINED,
        failure_type=finding_type,
        failure_description=description,
        failure_nature=category,
        correction_problem=str(boundary.get("problem_to_resolve", "")),
        required_property=str(boundary.get("required_property", "")),
        dual_status=DualStatus.UNRESOLVED,
        dual_property="",
        evidence=evidence,
        provenance_origin=f"BugShield:{scan_id}",
        input_hash=input_hash,
        extensions={"bugshield": payload},
    )
    return env.with_derived_dual()
