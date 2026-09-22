"""SARA — Testes da fusão ERU + Trindade."""
from sara.meta.eru_engine import ERU_Engine
from sara.meta.eru_trinity_bridge import ERUTrinityBridge
from sara.meta.eru_drift_detector import ERUDriftDetector
from sara.meta.eru_recovery_advisor import ERURecoveryAdvisor


def test_eru_bridge_observes_and_detects_drift():
    eru = ERU_Engine()
    bridge = ERUTrinityBridge(eru)
    bridge.observe("c1", "INPUT", {"state": {"a": 1, "keep": True}})
    bridge.observe("c1", "AFTER", {"state": {"keep": True, "b": 2}})
    audit = bridge.audit_cycle("c1")
    assert audit["ok"] is True
    assert audit["drifts"]
    assert audit["drifts"][0]["lost_count"] >= 1


def test_eru_recovery_advisor_only_proposes():
    eru = ERU_Engine()
    eru.freeze("old", {"capability": "x", "keep": 1})
    eru.freeze("new", {"keep": 1, "added": 2})
    advisor = ERURecoveryAdvisor(eru)
    candidates = advisor.find_lost_capabilities("old", "new")
    assert any(c["path"] == "capability" for c in candidates)
    proposal = advisor.propose_reintegration("old", "new")
    assert proposal["approval_required"] is True
    assert proposal["state_fused"]["capability"] == "x"


def test_eru_drift_classification():
    eru = ERU_Engine()
    detector = ERUDriftDetector(eru)
    eru.freeze("a", {"x": 1})
    eru.freeze("b", {"x": 1})
    report = detector.compute_drift("a", "b")
    assert report["score"] == 0
    assert report["classification"] == "estável"


def test_unified_trinity_keeps_existing_api():
    from sara.bootstrap import build_default_system
    system = build_default_system(fail_closed=True)
    unified = system.components["trinity_eru"]
    assert unified.describe()["status"] == "IMPLEMENTED"
    assessed = unified.assess("promover autonomia com transparência")
    assert assessed["ethics"]["approved"] is True
