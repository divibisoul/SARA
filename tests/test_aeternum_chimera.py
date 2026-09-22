
from sara.bootstrap import build_default_system


def test_aeternum_chimera_bridge_is_registered_with_real_dependencies():
    system = build_default_system(fail_closed=True)
    bridge = system.components["aeternum_chimera"]
    description = bridge.describe()

    assert bridge.NAME == "AeternumChimeraBridge"
    assert description["governance_authority"] == "GovernedSARA"
    assert description["reversibility_authority"] == "ERU_Engine"
    assert description["quantum_compute_status"] == "BLOCKED_INFRASTRUCTURE"


def test_aeternum_chimera_bridge_fuses_real_governance_and_eru_evidence():
    system = build_default_system(fail_closed=True)
    bridge = system.components["aeternum_chimera"]

    proposal = {
        "name": "aeternum-bridge-test",
        "description": "autonomia transparência consentimento integridade",
        "license": "MIT",
    }
    result = bridge.fuse_assessment(proposal)

    assert result["status"] == "FUSED_REAL"
    assert result["eru_snapshot"]["hash"]
    assert "accepted" in result["governance"]
    assert result["quantum_compute"]["status"] == "BLOCKED_INFRASTRUCTURE"
