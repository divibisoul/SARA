from sara.meta.soul_external_fabric import EXTERNAL_PROVIDERS, fabric_manifest, providers_for_function, resolve_external_provider

def test_external_fabric_has_25_sources():
    assert len(EXTERNAL_PROVIDERS)==25
    assert resolve_external_provider("mem0").revision=="abb81c88e1f738a8117d8293530fbc31a5ef8fd9"
    assert resolve_external_provider("langfuse").canonical_owner=="N07"
    assert resolve_external_provider("pydantic-ai").canonical_owner=="N01"

def test_function_affinity_is_deterministic():
    assert providers_for_function("mem0.add@1.0.0")[0].id=="mem0"
    assert providers_for_function("sara.trace")[0].id=="langfuse"

def test_unknown_provider_fails_closed():
    try:
        resolve_external_provider("unknown")
    except ValueError as exc:
        assert "SARA_EXTERNAL_PROVIDER_UNKNOWN" in str(exc)
    else:
        raise AssertionError("unknown provider did not fail closed")
