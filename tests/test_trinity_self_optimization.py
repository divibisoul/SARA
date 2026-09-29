"""Regression tests for the current additive Trinity self-optimization layer."""
from sara.bootstrap import build_default_system
from sara.core.trinity_self_optimization import from_sara_system


def test_current_trinity_self_optimization_executes_real_layers():
    system = build_default_system(fail_closed=True)
    optimizer = from_sara_system(system, max_passes=1)
    report = optimizer.run(max_passes=1)

    assert report.passes == 1
    assert len(report.integrity_hash) == 64
    assert report.ara_self["source_status"] == "REAL"
    assert report.etr_self["evidence_sufficient"] is True
    assert "optimization" in report.itr_self or "new_steps" in report.itr_self
    assert "combined" in report.etr_cross_validation
    assert "iterations" in report.trinity_cycle


def test_current_trinity_self_optimization_is_observational():
    system = build_default_system(fail_closed=True)
    optimizer = from_sara_system(system, max_passes=1)

    before = {
        "ara": system.components["ara_extended"].describe(),
        "etr": system.components["etr_extended"].describe(),
        "itr": system.components["itr_extended"].describe(),
    }
    report = optimizer.run(max_passes=1)
    after = {
        "ara": system.components["ara_extended"].describe(),
        "etr": system.components["etr_extended"].describe(),
        "itr": system.components["itr_extended"].describe(),
    }

    assert before == after
    assert report.integrity_hash
