from datetime import datetime, timezone

import pytest

from sara.core.provenance import Provenance, ProvenanceTracker
from sara.infra.vagus_bus import VagusNerveBus
from sara.rgo.contracts import RGOValidationError
from sara.rgo.engine import RGOEngine


def valid_finding(required_property: str = "validate before use") -> dict:
    return {
        "schema_version": "1.0.0",
        "finding_id": "sara-rgo-test-1",
        "object_id": "object-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": "corr-1",
        "trace_id": "trace-1",
        "source": {"system": "BugShield", "module": "Scanner", "version": "1.2.0"},
        "epistemic": {"mode": "INSPECTION", "verification_state": "VERIFIED"},
        "actionability": {"status": "ACTIONABLE"},
        "failure": {"type": "BUG", "description": "real test failure", "nature": "validation"},
        "correction_boundary": {
            "problem_to_resolve": "prevent the test failure",
            "required_property": required_property,
        },
        "dual": {"status": "UNRESOLVED"},
        "evidence": [{"id": "ev-1", "kind": "test", "ref": "test://rgo"}],
        "provenance": {"origin": "test", "input_hash": "sha256:test"},
    }


def test_rgo_uses_existing_provenance_and_vagus_bus():
    tracker = ProvenanceTracker()
    bus = VagusNerveBus()
    seen = []
    bus.subscribe("RGO_FINDING_RECEIVED", lambda event: seen.append(event["event_id"]))

    engine = RGOEngine(provenance=tracker, vagus_bus=bus)
    result = engine.ingest(valid_finding())

    assert result["status"] == "ACCEPTED"
    assert result["dual"]["status"] == "DERIVED_FROM_CONTRACT"
    assert seen
    assert tracker.verify_integrity()
    assert engine.state().integrity


def test_rgo_does_not_invent_dual():
    tracker = ProvenanceTracker()
    engine = RGOEngine(provenance=tracker)
    result = engine.ingest(valid_finding(required_property=""))
    assert result["dual"]["status"] == "UNRESOLVED"


def test_rgo_rejects_without_material_evidence():
    tracker = ProvenanceTracker()
    engine = RGOEngine(provenance=tracker)
    finding = valid_finding()
    finding["evidence"] = []
    with pytest.raises(RGOValidationError):
        engine.ingest(finding)
    assert engine.state().rejected == 1


def test_rgo_rejects_unknown_schema():
    tracker = ProvenanceTracker()
    engine = RGOEngine(provenance=tracker)
    finding = valid_finding()
    finding["schema_version"] = "9.9.9"
    with pytest.raises(RGOValidationError):
        engine.ingest(finding)
