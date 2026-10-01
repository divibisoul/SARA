from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from sara.meta.orbital_prefrontal import N07OrbitalPrefrontalAdapter


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        assert body["operation"] == "prefrontal.orbital.evaluate@1.0.0"
        assert self.headers["X-Correlation-ID"] == "corr-sara-orbit"
        payload = {"status": "ok", "metadata": {"simulation_is_not_hardware": "true"}}
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_args):
        return


def test_n07_orbital_prefrontal_adapter_preserves_contract():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        adapter = N07OrbitalPrefrontalAdapter(
            f"http://127.0.0.1:{server.server_port}",
            token="test-token",
        )
        result = adapter.evaluate(
            correlation_id="corr-sara-orbit",
            payload=[1.0, 2.0, 3.0, 4.0],
            workloads=[{
                "ID": "sara-orbit",
                "Operation": "reasoning-simulation",
                "Precision": "fp16",
                "MatrixSize": 256,
                "BatchSize": 1,
                "DataBytes": 4096,
                "MemoryNeeded": 1,
            }],
            candidate={"ID": "sara-candidate", "Cost": 0.1, "Risk": 0.1, "Utility": 0.9},
        )
        assert result.status == "200"
        assert result.correlation_id == "corr-sara-orbit"
        assert result.payload["metadata"]["simulation_is_not_hardware"] == "true"
    finally:
        server.shutdown()
        server.server_close()
