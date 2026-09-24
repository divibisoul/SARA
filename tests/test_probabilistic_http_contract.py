from __future__ import annotations

import os
import threading
import json
import urllib.request
import urllib.error

from sara.service.http_api import create_server


def _request(server, path, token, body):
    host, port = server.server_address
    request = urllib.request.Request(
        f"http://{host}:{port}{path}",
        method="POST",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_probabilistic_http_cycle_and_capability_contract():
    old = os.environ.get("PROBABILISTIC_LAYER")
    os.environ["PROBABILISTIC_LAYER"] = "true"
    os.environ["SARA_API_TOKEN"] = "prob-http-token-001"
    server = create_server("127.0.0.1", 0, fail_closed=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, body = _request(
            server,
            "/v1/cycle",
            "prob-http-token-001",
            {
                "input": "validar contexto probabilístico",
                "cycle_id": "http-prob-001",
                "context": {
                    "session_id": "http-session-001",
                    "client": "web",
                    "probabilistic": {
                        "structure": {"edges": []},
                        "nodes": [{
                            "name": "uncertainty",
                            "states": ["low", "high"],
                            "prior": {"low": 0.5, "high": 0.5},
                            "pseudo_counts": 1.0,
                            "evidence": {"high": 1.0},
                            "provenance": "USER",
                            "neural": {"logits": [0.0, 1.0]},
                        }],
                    },
                },
            },
        )
        assert status == 200
        node = body["probabilistic"]["nodes"][0]
        assert node["source"] == "fused"
        assert node["dirichlet_posterior"] is not None
        assert node["neural_posterior"] is not None

    finally:
        server.shutdown()
        server.server_close()
        if old is None:
            os.environ.pop("PROBABILISTIC_LAYER", None)
        else:
            os.environ["PROBABILISTIC_LAYER"] = old