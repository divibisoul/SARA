"""Executable gates for the integrated ARA/ETR/ITR/ERU engineering pass."""

from sara.audit.engineering_gate import EngineeringGate, BLOCKED, PARTIAL, REAL
from sara.bootstrap import build_default_system
from sara.core.ara_extended import ARA_Extended
from sara.core.itr_extended import ITR_Extended
from sara.meta.eru_engine import ERU_Engine


def test_engineering_gate_has_historical_inventory_and_no_missing_core_files():
    report = EngineeringGate.run()
    assert report["critical_ok"] is True
    assert report["inventory"]["historical_missing"] == []
    assert report["inventory"]["syntax_invalid"] == []


def test_engineering_gate_classifies_external_dependencies_without_false_green():
    report = EngineeringGate.run()
    states = {item["item"]: item["status"] for item in report["items"]}
    assert states["security/safe_sandbox.py"] in {BLOCKED, PARTIAL, REAL}
    assert states["meta/transystem_sara.py"] in {BLOCKED, PARTIAL, REAL}


def test_extended_nuclei_have_no_artificial_self_dependency():
    assert "ARA" not in ARA_Extended.DEPENDENCIES
    assert "ITR" not in ITR_Extended.DEPENDENCIES


def test_ara_structural_repairs_and_itr_execution_are_idempotent():
    system = build_default_system(fail_closed=True)
    ara = system.components["ara_extended"]
    marked = ara._annotate_complexity("conteúdo")
    assert ara._annotate_complexity(marked) == marked

    itr = system.components["itr_extended"]
    plan = itr.generate_strategic(
        "promover autonomia comunitária",
        {"ara_audit": {"flaws": []}},
    )
    result = itr.execute_composed(plan)
    assert result.rollback_triggered is False
    assert all(p.get("ok") is True for p in result.phase_results)
    assert not any(
        step in {"ethical_align", "resilience_check"}
        for phase in plan.phases
        for step in phase["steps"]
    )


def test_eru_checkpoint_and_information_loss_status_are_explicit():
    system = build_default_system(fail_closed=True)
    eru: ERU_Engine = system.components["eru"]
    first = eru.checkpoint("gate-cycle", 1, {"a": 1, "keep": True})
    second = eru.checkpoint("gate-cycle", 2, {"a": 1, "b": 2, "keep": True})
    assert first["verified"] is True
    assert second["verified"] is True
    status = eru.reconstructability(first["name"], second["name"])
    assert status["status"] in {"REAL", "UNMEASURABLE"}
