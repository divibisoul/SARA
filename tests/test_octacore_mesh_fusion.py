import os
import threading
import json
import urllib.request

from sara.bootstrap import build_default_system
from sara.meta.octacore_mesh_fusion import OCTACORE_SLOTS, SOUL_NUCLEI


def test_octacore_fusion_preserves_eight_slots_and_seven_mesh_nuclei():
    system = build_default_system(fail_closed=True)
    fusion = system.components["octacore_fusion"]

    description = fusion.describe()
    assert len(description["logical_octacore"]) == len(OCTACORE_SLOTS) == 8
    assert description["mesh"]["nuclei"] == list(SOUL_NUCLEI)
    assert len(description["mesh"]["nuclei"]) == 7
    assert description["mesh"]["sara_is_mesh_nucleus"] is False


def test_octacore_fusion_audits_real_registry_without_replacement():
    system = build_default_system(fail_closed=True)
    fusion = system.components["octacore_fusion"]

    report = fusion.audit()
    assert report["registry"]["module_count"] == system.registry.snapshot()["count"]
    assert report["definition"]["preservation"] == "additive"
    assert any(item["name"] == "g0_kernel" for item in report["checks"])
    assert any(item["name"] == "vagus_single_bus" for item in report["checks"])


def test_mesh_probe_is_unmeasurable_without_real_gateway_configuration(monkeypatch):
    monkeypatch.delenv("SOUL_MESH_N01_URL", raising=False)
    system = build_default_system(fail_closed=True)
    probe = system.components["octacore_fusion"].probe_mesh()

    assert probe.status == "UNMEASURABLE"
    assert probe.url is None
    assert probe.evidence_hash is None


def test_cycle_steps_reach_the_single_shared_vagus_bus():
    system = build_default_system(fail_closed=True)
    result = system.sistema_vivo.process(
        "preservar contexto e validar resultado",
        cycle_id="fusion-cycle-vagus-001",
    )

    history = system.components["vagus_bus"].get_history(limit=500)
    assert result.cycle_id == "fusion-cycle-vagus-001"
    assert any(
        event["event_type"] == "cycle.step"
        and event["correlation_id"] == "fusion-cycle-vagus-001"
        for event in history
    )


def test_hortacore_assessment_reaches_shared_vagus_bus():
    system = build_default_system(fail_closed=True)
    bridge = system.components["aeternum_chimera"]
    result = bridge.fuse_assessment({
        "name": "fusion-horta-test",
        "description": "preservar estado e rastreabilidade",
    })

    assert result["status"] == "FUSED_REAL"
    history = system.components["vagus_bus"].get_history(limit=200)
    assert any(
        event["event_type"] == "hortacore.assessment"
        and event["payload"]["proposal"] == "fusion-horta-test"
        for event in history
    )


def test_fusion_mesh_status_endpoint_does_not_claim_connection_without_probe():
    os.environ.pop("SOUL_MESH_N01_URL", None)
    from sara.service.http_api import create_server

    os.environ["SARA_API_TOKEN"] = "test-token-123456789"
    server = create_server("127.0.0.1", 0, fail_closed=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = urllib.request.Request(
            f"http://{host}:{port}/v1/mesh/status",
            headers={"Authorization": "Bearer test-token-123456789"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read())

        assert response.status == 200
        assert payload["proof"]["configured"] is False
        assert payload["proof"]["connected"] is False
        assert payload["proof"]["verified"] is False
    finally:
        server.shutdown()
        server.server_close()


def test_trinity_mirror_uses_stored_fused_hash_for_verification():
    system = build_default_system(fail_closed=True)
    trinity = system.components["trinity"]

    trinity.fuse_and_mirror(
        "fusion-trinity-hash-001",
        "test-target",
        {"flaws": ["x"], "semantic_fingerprint": "a"},
        {"approved": True, "consensus": 1.0},
        {"plan": ["step-1"]},
    )

    result = trinity.audit_mirror("fusion-trinity-hash-001")
    assert result["ok"] is True
    assert result["fused_hash"] == result["calculated_hash"]
