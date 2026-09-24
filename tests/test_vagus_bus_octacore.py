import asyncio

from sara.infra.vagus_bus import VagusNerveBus


def test_publish_sync_from_active_event_loop_does_not_call_asyncio_run():
    bus = VagusNerveBus()
    observed = []

    def health_callback(event):
        observed.append(event["event_type"])

    bus.subscribe("health.report", health_callback)

    async def exercise():
        def signal_callback(_event):
            bus.publish_sync(
                "SARA.G0",
                "VagusBus",
                "health.report",
                {"queue_depth": 0},
                correlation_id="corr-vagus-sync-001",
            )

        bus.subscribe("signal.throttle", signal_callback)
        await bus.publish(
            "G7",
            "SARA.G0",
            "signal.throttle",
            {"level": 1},
            correlation_id="corr-vagus-sync-001",
        )

    asyncio.run(exercise())

    assert "health.report" in observed
    assert any(
        event["correlation_id"] == "corr-vagus-sync-001"
        for event in bus.get_history()
    )


def test_vagus_bus_exposes_cloud_event_identity_and_target_routing():
    bus = VagusNerveBus()
    observed = []
    bus.subscribe("module.test", lambda event: observed.append(event), target="Target.A")
    bus.subscribe("module.test", lambda event: observed.append({"wrong": True}), target="Target.B")

    async def exercise():
        event = await bus.publish(
            "Source.A",
            "Target.A",
            "module.test",
            {"value": 7},
            correlation_id="corr-001",
            trace_id="trace-001",
            causation_id="cause-000",
            phase="audit",
            provenance="TEST",
        )
        assert event["specversion"] == "1.0"
        assert event["id"] == event["event_id"]
        assert event["type"] == "module.test"
        assert event["subject"] == "Target.A"
        assert event["data"]["value"] == 7
        assert event["trace_id"] == "trace-001"

    asyncio.run(exercise())
    assert len(observed) == 1
    assert observed[0]["target_module"] == "Target.A"


def test_vagus_registry_binding_and_forensic_structural_audit():
    from sara.bootstrap import build_default_system

    system = build_default_system(fail_closed=False)
    audit = system.components["vagus_forensic_audit"]
    assert audit["status"] == "VERIFIED"
    assert audit["vagus_unbound_modules"] == []
    assert audit["vagus_runtime_unbound_modules"] == []
    assert audit["vagus_missing_registration_evidence"] == []
    assert audit["contract_failures"] == []
    assert audit["dependency_failures"] == []
    assert audit["functional_execution"] == "UNMEASURABLE"
    assert audit["inventory"]["count"] == len(system.registry.items())
    assert len(system.components["vagus_bindings"]) == audit["inventory"]["count"]
    assert all(binding["runtime_bound"] for binding in system.components["vagus_bindings"].values())
