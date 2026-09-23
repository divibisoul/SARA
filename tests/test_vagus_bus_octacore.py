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
