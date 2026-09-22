"""Real SARA ↔ Clareira integration checks.

The tests use the actual SARA bootstrap and HTTP service implementation,
not a fake Clareira implementation.
"""
from __future__ import annotations

import json
import threading
from urllib.request import Request, urlopen

from sara.bootstrap import build_default_system
from sara.service.http_api import create_server


def _snapshot(correlation_id: str = "clareira-test-001") -> dict:
    return {
        "schemaVersion": "1.1.0",
        "blueprintVersion": "1.1.0",
        "timestamp": 1000,
        "status": "RUNNING",
        "metrics": {
            "totalNodes": 20,
            "activeNodes": 20,
            "averageLoad": 0.60,
            "averageTemperature": 0.30,
            "globalStress": 0.0,
            "turboActive": False,
            "packetsProcessed": 12,
            "tunelamentosRealizados": 1,
            "vagalTone": 0.50,
            "activeVagusBranches": 20,
            "timestamp": 1000,
        },
        "nodes": [
            {
                "id": "NC-001",
                "level": "Central",
                "active": True,
                "energy": 60,
                "energyCapacity": 100,
                "temperature": 0.30,
                "processingRate": 1,
                "packetsProcessed": 1,
                "queueSize": 0,
                "inputChannels": 1,
                "outputChannels": 1,
            },
            {
                "id": "NP-001",
                "level": "Primary",
                "active": True,
                "energy": 50,
                "energyCapacity": 100,
                "temperature": 0.30,
                "processingRate": 1,
                "packetsProcessed": 1,
                "queueSize": 0,
                "inputChannels": 1,
                "outputChannels": 1,
            },
        ],
        "channels": [{"id": "ch_NC-001_NP-001", "active": True}],
        "homeostasis": {"globalStress": 0.0, "energyScore": 55.0},
        "vagus": {
            "name": "VagusNerve",
            "version": "1.0.0",
            "active": True,
            "vagalTone": 0.5,
            "queuedAfferent": 0,
            "queuedEfferent": 0,
            "signalsIn": 0,
            "signalsOut": 0,
            "branches": [],
        },
    }


def test_clareira_is_registered_and_implements_real_ingestion():
    system = build_default_system(fail_closed=True)
    clareira = system.components["clareira"]

    assert "ClareiraSubsystem" in system.registration_report["registered"]
    assert system.ready is True
    result = clareira.ingest_snapshot(_snapshot(), correlation_id="clareira-test-001")

    assert result["observed_node_count"] == 2
    assert result["observed_channel_count"] == 1
    assert result["eru_hash"]
    assert system.components["eru"].has_snapshot("clareira:clareira-test-001:state")
    assert system.components["provenance"].verify_integrity() is True


def test_clareira_rejects_invalid_snapshot_without_mutating_last_state():
    system = build_default_system(fail_closed=True)
    clareira = system.components["clareira"]
    clareira.ingest_snapshot(_snapshot(), correlation_id="clareira-valid")
    before = clareira.latest_snapshot()

    invalid = dict(_snapshot("invalid"))
    del invalid["vagus"]

    try:
        clareira.ingest_snapshot(invalid, correlation_id="clareira-invalid")
    except ValueError as exc:
        assert "CLAREIRA_SNAPSHOT_MISSING:vagus" == str(exc)
    else:
        raise AssertionError("invalid snapshot was accepted")

    assert clareira.latest_snapshot() == before


def test_clareira_vagal_command_is_dispatched_only_to_real_event_bus():
    import asyncio

    system = build_default_system(fail_closed=True)
    clareira = system.components["clareira"]
    result = asyncio.run(
        clareira.issue_vagal_command(
            "NP-001",
            "calm",
            payload={"reason": "test"},
            priority=0.9,
            correlation_id="clareira-vagal-001",
        )
    )
    assert result["accepted"] is True
    assert result["executed"] is False
    history = clareira.bus.get_history()
    assert history[-1]["event_type"] == "CLAREIRA_VAGAL_COMMAND"
    assert history[-1]["payload"]["node_id"] == "NP-001"


def test_clareira_http_endpoints_call_canonical_runtime(monkeypatch):
    monkeypatch.setenv("SARA_API_TOKEN", "test-token")
    server = create_server("127.0.0.1", 0, fail_closed=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        payload = _snapshot("clareira-http-001")
        raw = json.dumps({
            "correlation_id": "clareira-http-001",
            "source": "SOUL_N01",
            "snapshot": payload,
        }).encode("utf-8")
        req = Request(
            f"http://127.0.0.1:{port}/v1/clareira/state",
            data=raw,
            method="POST",
            headers={
                "Authorization": "Bearer test-token",
                "Content-Type": "application/json",
                "X-Correlation-ID": "clareira-http-001",
            },
        )
        with urlopen(req, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
            assert response.status == 200
            assert body["accepted"] is True
            assert body["executed"] is True
            assert body["result"]["eru_hash"]

        command = json.dumps({
            "node_id": "NP-001",
            "command": "calm",
            "priority": 0.8,
            "correlation_id": "clareira-http-vagal-001",
        }).encode("utf-8")
        req = Request(
            f"http://127.0.0.1:{port}/v1/clareira/vagus",
            data=command,
            method="POST",
            headers={
                "Authorization": "Bearer test-token",
                "Content-Type": "application/json",
                "X-Correlation-ID": "clareira-http-vagal-001",
            },
        )
        with urlopen(req, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
            assert response.status == 202
            assert body["accepted"] is True
            assert body["executed"] is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
