from sara.meta.soul_federation import (
    SARA_FEDERATION_CONTRACT_VERSION,
    SARA_OPERATIONS,
    SOUL_NUCLEUS_AFFINITIES,
    affinity_for,
    federation_manifest,
)


def test_federation_manifest_has_all_current_sara_operations():
    manifest = federation_manifest()
    assert manifest["contract_version"] == SARA_FEDERATION_CONTRACT_VERSION
    assert set(manifest["operations"]) == set(SARA_OPERATIONS)
    assert manifest["non_destructive"] is True
    assert manifest["proof_rule"]["connected"].startswith("real request")


def test_all_declared_soul_nuclei_have_explicit_affinity():
    nuclei = {item.nucleus for item in SOUL_NUCLEUS_AFFINITIES}
    assert nuclei == {"N01", "N02", "N03", "N04", "N05", "N06", "N07"}
    for nucleus in nuclei:
        affinity = affinity_for(nucleus)
        assert affinity is not None
        assert affinity.preferred_operations
        assert affinity.complementary_sara_modules
        assert affinity.connection_mode


def test_affinity_lookup_is_case_and_whitespace_tolerant():
    assert affinity_for(" n02 ") == affinity_for("N02")



def test_chimera_bridge_is_advertised_as_complementary_for_gateway_and_federation():
    assert "AeternumChimeraBridge" in affinity_for("N01").complementary_sara_modules
    assert "AeternumChimeraBridge" in affinity_for("N07").complementary_sara_modules

def test_sara_owns_operations_without_claiming_live_connectivity():
    manifest = federation_manifest()
    assert manifest["ownership"].startswith("SARA-owns")
    assert manifest["proof_rule"]["declared"] == "manifest-only"
    assert manifest["proof_rule"]["configured"] == "URL + credential available"
