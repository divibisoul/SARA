def test_g0_health_report_reaches_existing_vagus_bus():
    from sara.infra.vagus_bus import VagusNerveBus
    from sara.meta.octacore_kernel import OctaCoreG0Kernel

    bus = VagusNerveBus()
    kernel = OctaCoreG0Kernel(queue_capacity=2, vagus_bus=bus)
    kernel._publish_health("corr-g0-health-001")
    history = bus.get_history()
    assert history
    assert history[-1]["event_type"] == "health.report"
    assert history[-1]["source_module"] == "SARA.G0"
    assert history[-1]["correlation_id"] == "corr-g0-health-001"
