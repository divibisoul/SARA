from sara.bootstrap import build_default_system


def test_omega_is_registered_and_exposed():
    system = build_default_system()
    assert system.ready is True
    assert "SoulETROmegaSystem" in system.registration_report["registered"]
    assert "omega" in system.components
    assert system.components["omega"].describe()["device_specific"] is False
