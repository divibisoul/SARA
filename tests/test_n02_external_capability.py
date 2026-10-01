from __future__ import annotations

import pytest

from sara.meta.n02_external_capability import N02ExternalCapabilityAdapter


def test_requires_valid_n07_endpoint() -> None:
    with pytest.raises(ValueError, match="http/https"):
        N02ExternalCapabilityAdapter("n07.invalid")


def test_external_adapter_preserves_n07_execute_contract_and_correlation(monkeypatch) -> None:
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    observed = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers["Content-Length"])
            observed["headers"] = dict(self.headers)
            observed["body"] = json.loads(self.rfile.read(length))
            raw = json.dumps({"ok": True, "operation": "cooperation.exchange"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, fmt, *args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        adapter = N02ExternalCapabilityAdapter(
            f"http://127.0.0.1:{server.server_port}",
            token="n07-app-token",
        )
        result = adapter.execute(
            capability="strategic_planning",
            payload={"input": "x"},
            correlation_id="corr-sara-n07-001",
            workloads=[{"id": "w1"}],
            candidate={"capability": "strategic_planning", "cost": 0.2},
        )
        assert result.status == 200
        assert observed["headers"]["X-Correlation-ID"] == "corr-sara-n07-001"
        assert observed["body"]["operation"] == "cooperation.exchange@1.0.0"
        assert observed["body"]["payload"] == []
        metadata = observed["body"]["metadata"]
        assert metadata["target"] == "N02"
        assert metadata["capability"] == "strategic_planning"
        assert metadata["correlation_id"] == "corr-sara-n07-001"
        embedded = json.loads(metadata["payload"])
        assert embedded["metadata"]["prefrontal_orbital"] == "true"
    finally:
        server.shutdown()
        server.server_close()
