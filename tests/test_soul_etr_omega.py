from sara.omega import SoulETROmegaSystem
from sara.omega.nuclei import (
    AnalysisNucleus, AsymmetryNucleus, EntropyNucleus, RealityFilterNucleus,
    ETRGenesisSuite,
)
from sara.omega.models import ETRContext, ETRMetric


def _context():
    metrics = (
        ETRMetric("cpu_utilization", 20.0, "%", "test", "2026-09-22T00:00:00Z"),
        ETRMetric("memory_utilization", 40.0, "%", "test", "2026-09-22T00:00:00Z"),
        ETRMetric("disk_utilization", 50.0, "%", "test", "2026-09-22T00:00:00Z"),
    )
    return ETRContext("test-cycle", metrics)


def test_real_nuclei_analyze_observed_metrics():
    ctx = _context()
    reports = (
        AnalysisNucleus().analyze(ctx),
        AsymmetryNucleus().analyze(ctx),
        EntropyNucleus().analyze(ctx),
        RealityFilterNucleus().analyze(ctx),
    )
    assert all(r.ok for r in reports)
    assert reports[0].metrics[0].source == "test"
    assert reports[2].findings[0]["entropy_bits"] >= 0


def test_reality_filter_rejects_invalid_percentage():
    ctx = ETRContext(
        "bad",
        (ETRMetric("memory_utilization", 120.0, "%", "test", "2026-09-22T00:00:00Z"),),
    )
    assert not RealityFilterNucleus().analyze(ctx).ok


def test_omega_cycle_does_not_claim_unavailable_privileges():
    system = SoulETROmegaSystem()
    description = system.describe()
    assert description["device_specific"] is False
    assert description["android_privileged_operations"] == "external_adapter_required"


def test_omega_cycle_produces_real_evidence():
    report = SoulETROmegaSystem().run_cycle()
    assert report.cycle_id.startswith("omega-")
    assert report.evidence["scanner"] == "SystemMetricsScanner"
    assert isinstance(report.evidence["metrics"], list)

def test_omega_context_services_use_explicit_inputs_only():
    system = SoulETROmegaSystem()
    report = system.run_cycle(
        cycle_id="omega-context-test",
        facts={
            "habit_key": "open_documents",
            "habit_candidates": ["open_documents", "other"],
            "habit_context": {"source": "test"},
            "battery_percent": 15,
            "network": "offline",
            "hour": 2,
            "completed_cycles": 10,
            "observed_reward": 0.8,
        },
    )
    assert report.cycle_id == "omega-context-test"
    assert report.evidence["habit"]["observation"]["count"] == 1
    assert "reduce_optional_work" in report.evidence["anticipation"]["recommendations"]
    assert "defer_network_work" in report.evidence["anticipation"]["recommendations"]
    assert report.evidence["micro_macro"]["completion_source"] == "explicit_fact"
    assert report.adaptation["updated"] is True
    assert report.adaptation["reward_source"] == "external_observation"



def test_gc_action_remains_available_but_is_not_claimed_reversible():
    action = ETRGenesisSuite().symbiosis._gc_action()
    assert action.id == "omega-gc"
    assert action.reversible is False

def test_omega_does_not_fabricate_adaptive_reward():
    report = SoulETROmegaSystem().run_cycle()
    assert report.adaptation["updated"] is False
    assert report.adaptation["reason"] == "no_observed_reward"
