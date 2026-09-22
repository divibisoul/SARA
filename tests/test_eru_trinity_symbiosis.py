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

def test_eru_capability_snapshot_detects_method_signature_and_contract_drift():
    from sara.core.provenance import ProvenanceTracker

    class DemoV1:
        NAME = "Demo"
        VERSION = "1.0"
        STATUS = type("S", (), {"value": "IMPLEMENTED"})()
        ROLE = type("R", (), {"value": "meta"})()
        DEPENDENCIES = ("A",)
        CYCLE_PHASES = ()

        def describe(self):
            return {
                "name": self.NAME,
                "version": self.VERSION,
                "status": self.STATUS.value,
                "role": self.ROLE.value,
                "dependencies": list(self.DEPENDENCIES),
                "phases": list(self.CYCLE_PHASES),
            }

        def alpha(self, value):
            return value

    class DemoV2(DemoV1):
        VERSION = "2.0"
        DEPENDENCIES = ("A", "B")

        def alpha(self, value, extra=None):
            return value

        def beta(self):
            return True

    eru = ERU_Engine(provenance=ProvenanceTracker())
    h1 = eru.freeze_capabilities("demo-v1", DemoV1())
    h2 = eru.freeze_capabilities("demo-v2", DemoV2())
    assert h1 != h2

    diff = eru.capability_diff("CAP::demo-v1", "CAP::demo-v2")
    assert diff["added_methods"] == ["beta"]
    assert diff["changed_methods"] == ["alpha"]
    assert diff["changed_contract"] == ["dependencies", "version"]
    assert diff["functional_equivalence_proven"] is False


def test_eru_recovery_preserves_none_values():
    eru = ERU_Engine()
    eru.freeze("old-none", {"feature": None, "keep": 1})
    eru.freeze("new-none", {"keep": 1})
    recovery = eru.recover("old-none", "new-none")
    assert recovery["state_fused"]["feature"] is None
    assert "feature" in recovery["recovered_paths"]
def test_bridge_capability_observation_and_drift():
    class V1:
        def describe(self):
            return {"name": "V1", "version": "1.0", "status": "IMPLEMENTED",
                    "role": "meta", "dependencies": [], "phases": []}

        def alpha(self, value):
            return value

    class V2:
        def describe(self):
            return {"name": "V2", "version": "2.0", "status": "IMPLEMENTED",
                    "role": "meta", "dependencies": [], "phases": []}

        def alpha(self, value, extra=None):
            return value

        def beta(self):
            return True

    eru = ERU_Engine()
    bridge = ERUTrinityBridge(eru)
    bridge.register_trinity(V1(), V1(), V1())
    bridge.observe("cap-cycle", "INPUT", {"state": "before"})
    bridge.observe_capabilities("cap-cycle", "INPUT")

    bridge.register_trinity(V2(), V2(), V2())
    bridge.observe("cap-cycle", "FINAL", {"state": "after"})
    bridge.observe_capabilities("cap-cycle", "FINAL")

    audit = bridge.audit_cycle("cap-cycle")
    assert audit["capability_drifts"]
    assert any(
        "alpha" in item["changed_methods"]
        for item in audit["capability_drifts"]
    )
    assert any(
        item["role"] == "ARA"
        for item in audit["capability_drifts"]
    )
def test_live_regenerative_loop_is_observed_by_eru():
    from sara.bootstrap import build_default_system

    system = build_default_system(fail_closed=True)
    result = system.sistema_vivo.process(
        "promover autonomia comunitária",
        cycle_id="eru-live-cycle",
    )
    assert result.loop_report.converged is True

    bridge = system.components["eru_bridge"]
    assert "eru-live-cycle" in bridge.observed_cycle_ids()
    audit = bridge.audit_cycle("eru-live-cycle")
    assert audit["observations"]
    assert audit["capability_observations"]
    assert audit["capability_drifts"]

def test_eru_capability_recovery_candidates():
    class Old:
        def describe(self):
            return {"name": "Old", "version": "1.0", "status": "IMPLEMENTED",
                    "role": "meta", "dependencies": [], "phases": []}

        def keep(self):
            return "keep"

        def lost(self):
            return "lost"

    class New:
        def describe(self):
            return {"name": "New", "version": "2.0", "status": "IMPLEMENTED",
                    "role": "meta", "dependencies": [], "phases": []}

        def keep(self):
            return "keep"

    eru = ERU_Engine()
    old = Old()
    new = New()
    eru.freeze_capabilities("old", old)
    eru.freeze_capabilities("new", new)
    advisor = ERURecoveryAdvisor(eru)
    candidates = advisor.find_lost_capabilities("CAP::old", "CAP::new")
    lost = [c for c in candidates if c["path"] == "method:lost"]
    assert len(lost) == 1
    assert lost[0]["recoverable"] is True
    assert lost[0]["automatic_reintegration"] is False
