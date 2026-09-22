"""Operational tests: real bootstrap, invariants, traceability and regeneration."""
from sara.bootstrap import build_default_system
from sara.contracts.invariants import InvariantValidator


def test_bootstrap_is_ready():
    system = build_default_system()
    assert system.ready is True
    assert system.invariant_report["ok"] is True
    assert system.registration_report["failed"] == []


def test_all_pending_modules_are_explicit():
    system = build_default_system()
    pending = set(system.registration_report["pending"])
    assert "SafeSandbox" in pending
    assert "QuantumCrawler" in pending
    assert "QuantumScanner" in pending
    assert "TransystemSARA" in pending
    assert "LegalAI" in pending


def test_cycle_has_12_canonical_phases_and_evidence():
    system = build_default_system()
    result = system.sistema_vivo.process("promover autonomia e transparência comunitária")
    report = result.loop_report
    phases = [s["phase"] for s in report.context_steps]
    expected = [
        "ingestion", "audit", "regeneration", "identity", "ethics",
        "strategy", "execution", "validation", "persistence",
        "snapshot", "monitoring", "governance",
    ]
    assert all(p in phases for p in expected)
    assert report.execution_report["trace_integrity"] is True
    assert report.execution_report["evidence_hash"]


def test_registry_invariants_are_checked_before_cycle():
    system = build_default_system()
    report = InvariantValidator().validate_registry(system.registry)
    assert report.ok is True
