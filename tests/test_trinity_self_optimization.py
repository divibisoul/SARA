"""Testes da camada adicional de auto-otimização da Trindade."""

from sara.bootstrap import build_default_system
from sara.core.trinity_self_optimization import TrinitySelfOptimizer, from_sara_system


def test_trinity_self_optimizer_executes_all_cross_layers():
    system = build_default_system(fail_closed=True)
    optimizer = from_sara_system(system, max_passes=2)

    report = optimizer.run(max_passes=2)

    assert report.passes >= 1
    assert isinstance(report.integrity_hash, str)
    assert len(report.integrity_hash) == 64
    assert report.ara_self
    assert report.etr_self
    assert report.itr_self
    assert report.ara_cross_audit
    assert report.etr_cross_validation
    assert report.itr_cross_analysis
    assert report.trinity_cycle
    assert report.proposals["ARA"]
    assert report.proposals["ETR"]
    assert report.proposals["ITR"]
    assert isinstance(report.findings, tuple)


def test_trinity_self_optimizer_is_additive_and_observational():
    system = build_default_system(fail_closed=True)
    optimizer = TrinitySelfOptimizer(
        system.components["ara_extended"],
        system.components["etr_extended"],
        system.components["itr_extended"],
        synergy=system.components["trinity"],
        max_passes=2,
    )

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
    assert report.stable is False
    assert optimizer.history()
