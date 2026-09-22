"""Tests da arquitetura conectada do SARA.

Estes testes não simulam infraestrutura externa; verificam contratos locais,
grafo de dependências e integração real dos módulos disponíveis.
"""
from sara.bootstrap import build_default_system
from sara.contracts.base import CyclePhase


def test_bootstrap_registers_connected_runtime_and_dependency_graph():
    system = build_default_system(fail_closed=True)
    assert system.ready is True
    assert "ConnectedRuntime" in system.registration_report["registered"]
    connection = system.components["connected_runtime"].validate_connection()
    assert connection["ok"] is True
    assert connection["connected_count"] == system.registry.snapshot()["count"]


def test_connected_runtime_dispatches_real_non_core_operations():
    system = build_default_system(fail_closed=True)
    runtime = system.components["connected_runtime"]
    trace = system.components["trace"]
    temporal = system.components["temporal"]

    from sara.contracts.context import CycleContext, TraceSink
    ctx = CycleContext(
        "test-connected",
        "texto de ciclo SARA com autonomia, transparência e comunidade",
        "texto de ciclo SARA com autonomia, transparência e comunidade",
        TraceSink(trace, temporal, system.components["provenance"]),
    )

    actions = runtime.dispatch_phase(ctx, CyclePhase.PERSISTENCE)
    names = {a.module for a in actions}
    assert "ERU_Engine" in names
    assert any(a.operation == "eru_freeze" and a.ok for a in actions)


def test_system_vivo_blocks_when_connection_invariants_fail():
    system = build_default_system(fail_closed=True)
    runtime = system.components["connected_runtime"]
    original = runtime._registry.dependency_order

    runtime._registry.dependency_order = lambda: (_ for _ in ()).throw(
        RuntimeError("forced_graph_failure")
    )
    try:
        try:
            system.sistema_vivo.process("entrada")
            assert False, "SistemaVivo deveria bloquear o ciclo"
        except RuntimeError as exc:
            assert "invariantes" in str(exc)
    finally:
        runtime._registry.dependency_order = original
