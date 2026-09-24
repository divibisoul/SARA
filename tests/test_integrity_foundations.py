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


def test_dna_tags_violation_chain_is_verifiable():
    from sara.memory.dna_tags import DNA_Tags
    dna = DNA_Tags()
    result = dna.explain_guard("alterar", "texto 🔒CORE")
    assert result["blocked"] is True
    assert result["integrity"] is True


def test_quantum_snapshot_chain_is_verifiable():
    from sara.meta.quantum_snapshot import QuantumSnapshotSystem
    snapshots = QuantumSnapshotSystem()
    first = snapshots.snapshot({"state": {"x": 1}})
    second = snapshots.snapshot({"state": {"x": 2}})
    assert first != second
    assert snapshots.restore(first)["state"]["x"] == 1
    assert snapshots.verify_integrity() is True


def test_decision_trace_ipfs_path_requires_real_endpoint():
    from sara.monitoring.decision_trace import DecisionTrace
    trace = DecisionTrace()
    entry = trace.log({"event": "test"})
    assert trace.verify() is True
    with __import__("pytest").raises(RuntimeError, match="IPFS_NOT_CONFIGURED"):
        trace.publish_to_ipfs(entry)

def test_governance_override_preserves_chain_integrity():
    governance = GovernanceBackend({"SARA": "IMPLEMENTED"})
    governance.register_decision({"event": "decision", "accepted": True})
    result = governance.override(0, "revalidate")
    assert result["chain_integrity"] is True
    assert governance.verify_integrity() is True
    assert governance.decisions()[0]["override"]["action"] == "revalidate"
    assert governance.decisions()[-1]["event"] == "decision_override"

def test_governance_filtered_decisions_preserve_original_override_index():
    governance = GovernanceBackend({"SARA": "IMPLEMENTED"})
    governance.register_decision({"event": "first"})
    governance.register_decision({"event": "second"})
    governance.override(1, "revalidate-second")
    since = governance.decisions()[1]["ts"]
    filtered = governance.decisions(since=since)
    assert filtered[0]["event"] in {"second", "decision_override"}
    second = next(item for item in filtered if item.get("event") == "second")
    assert second["override"]["action"] == "revalidate-second"
