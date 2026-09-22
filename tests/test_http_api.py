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


def _request(server, path, method="GET", body=None, token=None):
    host, port = server.server_address
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"http://{host}:{port}{path}",
        method=method,
        data=data,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
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
        )
        assert status == 200
        assert payload["cycle_id"]
        assert payload["final_state"]
    finally:
        server.shutdown()
        server.server_close()
