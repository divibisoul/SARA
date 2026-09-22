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
    nodes = []
    levels = ["Central", *["Primary"] * 12, *["Secondary"] * 48]
    for index, level in enumerate(levels, start=1):
        node_id = "NC-001" if level == "Central" else (
            f"NP-{index - 1:03d}" if level == "Primary" else f"MS-{index - 13:03d}"
        )
        nodes.append(
            {
                "id": node_id,
                "level": level,
                "active": True,
                "energy": 60,
                "energyCapacity": 100,
                "temperature": 0.30,
                "processingRate": 1,
                "packetsProcessed": 1,
                "queueSize": 0,
                "inputChannels": 1,
                "outputChannels": 1,
            }
        )

    channels = []
    primary_ids = [f"NP-{i:03d}" for i in range(1, 13)]
    secondary_ids = [f"MS-{i:03d}" for i in range(1, 49)]
    for primary in primary_ids:
        channels.append({"id": f"ch_{primary}_NC-001", "active": True})
        channels.append({"id": f"ch_NC-001_{primary}", "active": True})
    for index, secondary in enumerate(secondary_ids):
        primary = primary_ids[index // 4]
        channels.append({"id": f"ch_{secondary}_{primary}", "active": True})
        channels.append({"id": f"ch_{primary}_{secondary}", "active": True})

    return {
        "schemaVersion": "1.1.0",
        "blueprintVersion": "1.1.0",
        "timestamp": 1000,
        "status": "RUNNING",
        "metrics": {
            "totalNodes": 61,
            "activeNodes": 61,
            "averageLoad": 0.60,
            "averageTemperature": 0.30,
            "globalStress": 0.0,
            "turboActive": False,
            "packetsProcessed": 61,
            "tunelamentosRealizados": 1,
            "vagalTone": 0.50,
            "activeVagusBranches": 61,
            "timestamp": 1000,
        },
        "nodes": nodes,
        "channels": channels,
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

    assert result["observed_node_count"] == 61
    assert result["observed_channel_count"] == 120
    assert result["eru_hash"]
    assert system.components["eru"].has_snapshot("clareira:clareira-test-001:state")
    assert system.components["provenance"].verify_integrity() is True

    snapshot = _snapshot()
    snapshot["deviceState"] = {
        "batteryPercent": 38,
        "charging": False,
        "batteryTemperatureC": 39.5,
        "screenOn": True,
        "network": "Wi-Fi",
        "shizukuStatus": "AUTHORIZED",
        "timestamp": 1000,
    }
    second = clareira.ingest_snapshot(snapshot, correlation_id="clareira-device-001")
    assert second["device_state"]["batteryPercent"] == 38


def test_clareira_frontier_fuses_eru_mmd_rgo_and_trinity_without_execution_claims():
    system = build_default_system(fail_closed=True)
    clareira = system.components["clareira"]
    frontier = system.components["clareira_frontier"]

    clareira.ingest_snapshot(_snapshot("frontier-001"), correlation_id="frontier-001")
    first = frontier.assess_latest(correlation_id="frontier-audit-001")
    assert first["mmd"]["counts"]["missing"] == 0
    assert first["mmd"]["counts"]["changed"] == 0
    assert first["rgo"]["execution_status"] == "NOT_EXECUTED"
    assert first["trinity"]["execution_status"] == "NOT_EXECUTED"
    assert first["eru"]["transition_audited"] is False

    changed = _snapshot("frontier-002")
    changed["nodes"][0]["energy"] = 55
    changed["metrics"]["averageLoad"] = 0.55
    clareira.ingest_snapshot(changed, correlation_id="frontier-002")
    second = frontier.assess_latest(correlation_id="frontier-audit-002")

    assert second["eru"]["transition_audited"] is True
    assert second["mmd"]["counts"]["changed"] > 0
    assert second["rgo"]["status"] == "PROPOSED"
    assert second["rgo"]["complementary_capabilities"]
    assert all(
        item["execution_status"] == "PROPOSED"
        for item in second["rgo"]["complementary_capabilities"]
    )
    assert second["rgo"]["execution_status"] == "NOT_EXECUTED"
    assert second["trinity"]["assessment"]["strategy"]["phases"] >= 1
    assert second["eru"]["functional_equivalence_proven"] is False
    assert system.components["provenance"].verify_integrity() is True


def test_clareira_requires_canonical_topology():
    system = build_default_system(fail_closed=True)
    clareira = system.components["clareira"]
    invalid = _snapshot()
    invalid["nodes"] = invalid["nodes"][:1]
    try:
        clareira.ingest_snapshot(invalid, correlation_id="clareira-topology-invalid")
    except ValueError as exc:
        assert str(exc) == "CLAREIRA_TOPOLOGY_NODE_COUNT_INVALID"
        return
    raise AssertionError("non-canonical Clareira topology was accepted")


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


def test_clareira_vagal_delivery_moves_pending_to_acknowledged():
    import asyncio

    system = build_default_system(fail_closed=True)
    clareira = system.components["clareira"]

    dispatched = asyncio.run(
        clareira.issue_vagal_command(
            "NP-001",
            "calm",
            payload={"reason": "health"},
            priority=0.9,
            correlation_id="clareira-vagal-delivery-001",
        )
    )
    event_id = dispatched["event_id"]

    pending = clareira.pending_vagal_commands()
    assert any(item["event_id"] == event_id and item["delivery_status"] == "PENDING" for item in pending)

    acknowledged = clareira.acknowledge_vagal_command(
        event_id,
        executed=True,
        execution_status="APPLIED_IN_SOUL_RUNTIME",
    )
    assert acknowledged["delivery_status"] == "EXECUTED"
    assert acknowledged["execution_status"] == "APPLIED_IN_SOUL_RUNTIME"
    assert all(item["event_id"] != event_id for item in clareira.pending_vagal_commands())


def test_clareira_rejects_unauthorized_vagal_target():
    import asyncio

    system = build_default_system(fail_closed=True)
    clareira = system.components["clareira"]
    try:
        asyncio.run(
            clareira.issue_vagal_command(
                "NP-001",
                "calm",
                correlation_id="clareira-target-001",
                target="N02",
            )
        )
    except ValueError as exc:
        assert str(exc) == "CLAREIRA_VAGAL_TARGET_UNAUTHORIZED"
        return
    raise AssertionError("unauthorized vagal target was accepted")
