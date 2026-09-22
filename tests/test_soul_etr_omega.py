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
