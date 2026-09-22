"""Tests for integrity foundations strengthened during the connected build."""
from sara.core.provenance import Provenance, ProvenanceTracker
from sara.memory.regenerative_memory import RegenerativeMemory
from sara.security.emergency_rollback import EmergencyRollback
from sara.monitoring.governance import GovernanceBackend


def test_provenance_chain_is_verifiable():
    tracker = ProvenanceTracker()
    tracker.register("rule.a", Provenance.HISTORICAL, "source a")
    tracker.register("rule.b", Provenance.RECONSTRUCTED, "source b")
    assert tracker.verify_integrity() is True
    assert tracker.integrity_head() != "GENESIS"


def test_temporal_memory_structural_diff_and_integrity():
    memory = RegenerativeMemory()
    v1 = memory.store({"a": {"b": 1}, "items": [1, 2]}, "v1")
    v2 = memory.store({"a": {"c": 2}, "items": [1]}, "v2")
    diff = memory.diff(v1.id, v2.id)
    assert "a.b" in diff["lost"]
    assert "a.c" in diff["added"]
    assert "items[1]" in diff["lost"]
    assert memory.verify_integrity(v2.id) is True


def test_emergency_rollback_chain_is_verifiable():
    rollback = EmergencyRollback()
    first = rollback.capture("one", {"x": 1})
    second = rollback.capture("two", {"x": 2})
    assert first != second
    assert rollback.verify_chain() is True


def test_governance_override_changes_decision_record():
    governance = GovernanceBackend({"SARA": "IMPLEMENTED"})
    governance.register_decision({"event": "decision", "accepted": True})
    result = governance.override(0, "revalidate")
    assert result["ok"] is True
    assert governance.decisions()[0]["override"]["action"] == "revalidate"
