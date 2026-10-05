from sara.infra.vagus_bus import VagusNerveBus


class DemoModule:
    NAME = "DemoModule"
    VERSION = "1.0"
    STATUS = "IMPLEMENTED"
    ROLE = "UTILITY"
    DEPENDENCIES = ()
    CYCLE_PHASES = ()

    def describe(self):
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS,
            "role": self.ROLE,
            "dependencies": [],
            "phases": [],
        }

    def run(self, value: int):
        return value + 1


def test_vagus_retains_legacy_contract_and_adds_traceable_identity():
    bus = VagusNerveBus()
    seen = []
    bus.subscribe("module.test", lambda event: seen.append(event), target="Target.A")

    event = bus.publish_sync(
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

    assert event["event_id"] == event["id"]
    assert event["specversion"] == "1.0"
    assert event["subject"] == "Target.A"
    assert event["data"]["value"] == 7
    assert seen == [event]
    assert bus.replay(event_type="module.test", correlation_id="corr-001", target="Target.A", limit=1) == [event]


def test_vagus_ack_and_registry_binding_are_observable_without_replacing_module_logic():
    bus = VagusNerveBus()
    module = DemoModule()

    binding = bus.register_module(module)
    assert binding["runtime_bound"] is True
    assert binding["instrumented"] is True
    assert module._vagus_bus is bus

    assert module.run(4) == 5
    history_types = [item["event_type"] for item in bus.get_history()]
    assert "module.registered" in history_types
    assert "module.method.start" in history_types
    assert "module.method.complete" in history_types

    ack = bus.ack("message-001", "DemoModule", correlation_id="corr-ack")
    assert ack["status"] == "ACK"
    assert ack["payload"]["message_id"] == "message-001"

    bindings = bus.module_bindings()
    assert bindings["DemoModule"]["runtime_bound"] is True


def test_vagus_describe_is_explicit_about_non_external_delivery():
    description = VagusNerveBus().describe()
    assert description["version"] == "1.1"
    assert description["backend"] == "in_process"
    assert description["external_broker"] == "UNMEASURABLE"
