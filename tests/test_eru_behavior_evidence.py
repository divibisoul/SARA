from sara.meta.eru_engine import ERU_Engine
from sara.meta.eru_trinity_bridge import ERUTrinityBridge


class V1:
    def describe(self):
        return {"name": "Demo", "version": "1.0", "status": "IMPLEMENTED",
                "role": "meta", "dependencies": [], "phases": []}

    def alpha(self, value):
        return value


class V2:
    def describe(self):
        return {"name": "Demo", "version": "2.0", "status": "IMPLEMENTED",
                "role": "meta", "dependencies": [], "phases": []}

    def alpha(self, value):
        return value


def test_behavior_diff_is_scoped_to_explicitly_observed_probes():
    eru = ERU_Engine()
    eru.freeze_capabilities("old", V1())
    eru.freeze_capabilities("new", V2())

    eru.record_behavior_observation(
        "CAP::old", "alpha", "probe-1", "input-a", "output-a", success=True
    )
    eru.record_behavior_observation(
        "CAP::new", "alpha", "probe-1", "input-a", "output-a", success=True
    )
    result = eru.behavior_diff("CAP::old", "CAP::new")

    assert result["behavioral_evidence_available"] is True
    assert result["behaviorally_equivalent_for_observed_probes"] is True
    assert result["functional_equivalence_proven"] is False
    assert result["proof_scope"] == "observed_probes_only"


def test_behavior_diff_detects_observed_output_change():
    eru = ERU_Engine()
    eru.freeze_capabilities("old", V1())
    eru.freeze_capabilities("new", V2())

    eru.record_behavior_observation(
        "CAP::old", "alpha", "probe-1", "input-a", "output-a", success=True
    )
    eru.record_behavior_observation(
        "CAP::new", "alpha", "probe-1", "input-a", "output-b", success=True
    )
    result = eru.behavior_diff("CAP::old", "CAP::new")

    assert len(result["changed_observations"]) == 1
    assert result["behaviorally_equivalent_for_observed_probes"] is False


def test_trinity_bridge_can_attach_external_behavior_evidence_without_executing_methods():
    eru = ERU_Engine()
    bridge = ERUTrinityBridge(eru)
    bridge.register_trinity(V1(), V1(), V1())

    bridge.observe_capabilities("c-behavior", "INPUT")
    bridge.register_trinity(V2(), V2(), V2())
    bridge.observe_capabilities("c-behavior", "FINAL")

    for role in ("ARA", "ETR", "ITR"):
        bridge.record_behavior(
            "c-behavior", "INPUT", role, "alpha", "probe-1",
            "input-a", "output-a", success=True,
        )
        bridge.record_behavior(
            "c-behavior", "FINAL", role, "alpha", "probe-1",
            "input-a", "output-a", success=True,
        )

    audit = bridge.audit_cycle("c-behavior")
    assert len(audit["behavioral_evidence"]) == 6
    assert audit["behavioral_drifts"]
    assert all(item["functional_equivalence_proven"] is False
               for item in audit["behavioral_drifts"])
