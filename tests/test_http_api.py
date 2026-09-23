import json
import os
import threading
import urllib.request
import urllib.error

from sara.service.http_api import create_server


def _start_server():
    os.environ["SARA_API_TOKEN"] = "test-token-123456789"
    server = create_server("127.0.0.1", 0, fail_closed=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _request(server, path, method="GET", body=None, token=None, correlation_id=None):
    host, port = server.server_address
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"http://{host}:{port}{path}",
        method=method,
        data=data,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
            **({"X-Correlation-ID": correlation_id} if correlation_id else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_health_is_public_and_reports_runtime():
    server, _ = _start_server()
    try:
        status, payload = _request(server, "/health")
        assert status == 200
        assert payload["service"] == "SARA"
        assert payload["ready"] is True
        assert payload["invariants_ok"] is True
    finally:
        server.shutdown()
        server.server_close()


def test_v1_capabilities_requires_bearer_and_exposes_operations():
    server, _ = _start_server()
    try:
        status, _ = _request(server, "/v1/capabilities")
        assert status == 401
        status, payload = _request(
            server, "/v1/capabilities", token="test-token-123456789"
        )
        assert status == 200
        assert "sara.health@1.0.0" in payload["operations"]
        assert "sara.cycle@1.0.0" in payload["operations"]
        assert "sara.audit@1.0.0" in payload["operations"]
    finally:
        server.shutdown()
        server.server_close()


def test_audit_uses_real_ara_and_etr_paths():
    server, _ = _start_server()
    try:
        status, payload = _request(
            server,
            "/v1/audit",
            method="POST",
            body={"input": "preservar autonomia, transparência e comunidade"},
            token="test-token-123456789",
        )
        assert status == 200
        assert payload["operation"] == "audit"
        assert "ethical" in payload
        assert "provenance" in payload
    finally:
        server.shutdown()
        server.server_close()


def test_capabilities_include_federation_identity_and_trace():
    server, _ = _start_server()
    try:
        status, payload = _request(
            server, "/v1/capabilities", token="test-token-123456789"
        )
        assert status == 200
        assert payload["identity"]["node_id"] == "SARA"
        assert "sara.trace@1.0.0" in payload["operations"]
        trace_descriptor = next(
            d for d in payload["capability_descriptors"]
            if d["operation"] == "sara.trace@1.0.0"
        )
        assert trace_descriptor["endpoint"] == "/v1/trace/{cycle_id}"
        federation = payload["soul_federation"]
        assert federation["contract_version"] == "1.0.0"
        assert {item["nucleus"] for item in federation["nucleus_affinities"]} == {"N01", "N02", "N03", "N04", "N05", "N06", "N07"}
        memory_layers = payload["memory_layers"]
        assert memory_layers["working"]["layer"] == "working_memory"
        assert memory_layers["working"]["storage_scope"] == "process_ram_bounded"
        assert memory_layers["episodic"]["name"] == "RegenerativeMemory"
        assert memory_layers["semantic_vector"]["name"] == "TemporalVectorDB"
    finally:
        server.shutdown()
        server.server_close()


def test_cycle_propagates_correlation_id():
    server, _ = _start_server()
    try:
        status, payload = _request(
            server,
            "/v1/cycle",
            method="POST",
            body={"input": "preservar autonomia e validar resultado"},
            token="test-token-123456789",
            correlation_id="corr-http-test-001",
        )
        assert status == 200
        assert payload["cycle_id"]
        assert payload["request_id"] == "corr-http-test-001"
        assert payload["correlation_id"] == "corr-http-test-001"
        assert payload["final_state"]
    finally:
        server.shutdown()
        server.server_close()


def test_cycle_accepts_octacore_context():
    server, _ = _start_server()
    try:
        status, payload = _request(
            server,
            "/v1/cycle",
            method="POST",
            body={
                "input": "preservar autonomia e validar resultado",
                "context": {
                    "research_snippets": [{"source": "n04", "text": "contexto-real"}],
                    "probabilistic": {"alpha": 0.7, "beta": 0.3},
                    "pipeline_status": "pre-complete",
                },
            },
            token="test-token-123456789",
            correlation_id="corr-octacore-context-001",
        )
        assert status == 200
        assert payload["octacore_context"]["present"] is True
        assert set(payload["octacore_context"]["keys"]) == {
            "pipeline_status", "probabilistic", "research_snippets"
        }
        assert payload["correlation_id"] == "corr-octacore-context-001"
    finally:
        server.shutdown()
        server.server_close()


def test_vagus_endpoint_publishes_to_existing_bus():
    server, _ = _start_server()
    try:
        status, payload = _request(
            server,
            "/v1/vagus",
            method="POST",
            body={
                "vagus_version": "1.0",
                "message_id": "msg-vagus-001",
                "correlation_id": "corr-vagus-001",
                "source": "G7",
                "target": "G6",
                "priority": 90,
                "ttl": 5000,
                "type": "gpu.submit",
                "payload": {"job_id": "octa-vagus-001"},
            },
            token="test-token-123456789",
            correlation_id="corr-vagus-001",
        )
        assert status == 202
        assert payload["accepted"] is True
        assert payload["event"]["event_id"] == "msg-vagus-001"
        assert payload["event"]["correlation_id"] == "corr-vagus-001"
        system = server.sara_system
        history = system.components["vagus_bus"].get_history()
        assert any(event["event_id"] == "msg-vagus-001" for event in history)
    finally:
        server.shutdown()
        server.server_close()
