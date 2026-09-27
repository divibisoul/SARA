import asyncio

from sara.infra.vagus_bus import VagusNerveBus
from sara.meta.bayesian_uncertainty import BayesianMetaLearner
from sara.meta.eru_runtime import ERURuntime
from sara.memory.working_memory import WorkingMemory


def test_vagus_bus_routes_async_and_sync_subscribers():
    seen = []
    bus = VagusNerveBus()
    bus.subscribe("TEST", lambda event: seen.append(event["event_id"]))

    async def runner():
        event = await bus.publish("A", "B", "TEST", {"x": 1})
        assert event["status"] == "EXECUTE"

    asyncio.run(runner())
    assert len(seen) == 1
    assert len(bus.get_history()) == 1


def test_bayesian_meta_learner_is_explicit_about_its_evidence_scope():
    learner = BayesianMetaLearner()
    result = learner.evaluate(0.95, 0.95, 0.90)
    assert 0 <= result["posterior_confidence"] <= 1
    assert result["calibration_status"] == "EXPLICIT_INPUTS_ONLY"


def test_eru_runtime_does_not_fake_execution():
    async def runner():
        runtime = ERURuntime()
        result = await runtime.assess_and_route({
            "context_completeness": 0.1,
            "syntax_validity": 0.1,
            "historical_success_rate": 0.1,
        })
        assert result["status"] == "CONTEXT_REQUIRED"
        assert runtime.describe()["external_execution"] is False

    asyncio.run(runner())


def test_working_memory_is_bounded():
    memory = WorkingMemory(max_items=2)
    memory.put("a", 1)
    memory.put("b", 2)
    memory.put("c", 3)
    assert memory.get("a") is None
    assert memory.get("c") == 3


def test_working_memory_is_first_class_in_sara_bootstrap():
    from sara.bootstrap import build_default_system

    system = build_default_system(fail_closed=False)
    working = system.components["working_memory"]
    assert system.registry.get("WorkingMemory") is not None
    assert working.describe()["layer"] == "working_memory"
    assert working.describe()["storage_scope"] == "process_ram_bounded"



def test_eru_runtime_can_share_one_canonical_vagus_bus():
    bus = VagusNerveBus()
    runtime = ERURuntime(bus=bus)

    async def runner():
        await runtime.bus.publish(
            "ERU_RUNTIME",
            "SYSTEM",
            "TEST_SHARED_BUS",
            {"shared": True},
        )

    asyncio.run(runner())
    assert runtime.bus is bus
    assert bus.get_history()[0]["event_type"] == "TEST_SHARED_BUS"


def test_bootstrap_registers_one_canonical_vagus_bus():
    from sara.bootstrap import build_default_system

    system = build_default_system(fail_closed=False)
    bus = system.components["vagus_bus"]
    assert system.registry.get("VagusNerveBus") is bus
    assert bus.describe()["control_metadata"] == [
        "message_id", "correlation_id", "priority", "ttl"
    ]
