from sara.bootstrap import build_default_system


def test_aeternum_has_exactly_eight_bindings():
    system = build_default_system(fail_closed=True)
    adapter = system.components["aeternum_modules"]
    snapshot = adapter.snapshot()

    assert len(snapshot["bindings"]) == 8
    assert snapshot["validation"]["ok"] is True
    assert snapshot["validation"]["module_states"]["M6_IMMUNITY"] == "implemented"
    assert snapshot["validation"]["module_states"]["M7_EVOLUTION"] == "implemented"
    assert snapshot["validation"]["module_states"]["M8_GOVERNANCE_MEMORY"] == "implemented"


def test_aeternum_reuses_sara_federation_contract():
    system = build_default_system(fail_closed=True)
    adapter = system.components["aeternum_modules"]
    federation = adapter.snapshot()["sara_federation"]

    assert federation["system"] == "SOUL↔SARA"
    assert federation["contract_version"] == "1.0.0"
    assert federation["proof_rule"]["failed"] == "explicit error; never synthetic success"
