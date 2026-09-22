"""Current SARA engineering-gate regression tests."""
from sara.bootstrap import build_default_system
from sara.audit.engineering_gate import EngineeringGate, REAL, PARTIAL, BLOCKED


def test_engineering_gate_inventory_includes_current_extensions():
    report = EngineeringGate().audit()
    assert not report.inventory["historical_missing"]
    assert not report.inventory["syntax_invalid"]
    assert "memory/working_memory.py" not in report.inventory["historical_missing"]
    assert "omega/system.py" not in report.inventory["historical_missing"]
    assert "meta/aeternum_chimera.py" not in report.inventory["historical_missing"]
    assert report.inventory["python_files"] >= len(report.inventory["current_only_files"])


def test_bootstrap_exposes_current_integrated_components():
    system = build_default_system(fail_closed=True)
    assert system.ready is True
    for name in (
        "ara_extended", "etr_extended", "itr_extended",
        "eru", "eru_bridge", "trinity_eru",
        "working_memory", "omega", "aeternum_chimera",
    ):
        assert name in system.components


def test_anti_simulation_gate_reports_explicit_external_blockers():
    report = EngineeringGate().audit()
    statuses = {item.item: item.status for item in report.items}
    assert statuses["external::security/safe_sandbox.py"] in {BLOCKED, PARTIAL}
    assert statuses["external::research/quantum_crawler.py"] in {BLOCKED, PARTIAL}
    assert statuses["anti_simulation_static_scan"] in {REAL, PARTIAL}



def test_eru_checkpoint_reconstructability_and_information_loss():
    system = build_default_system(fail_closed=True)
    eru = system.components["eru"]
    first = eru.checkpoint(
        "before",
        {"keep": True, "remove": "recoverable"},
        cycle_id="gate-eru-001",
        phase="audit",
    )
    second = eru.checkpoint(
        "after",
        {"keep": True},
        cycle_id="gate-eru-001",
        phase="regeneration",
    )
    assert first["verified"] is True
    assert second["verified"] is True
    loss = eru.detect_information_loss(first["name"], second["name"])
    assert loss["status"] == "REAL"
    assert loss["loss_detected"] is True
    assert "remove" in loss["recoverable"]
    reconstruction = eru.reconstructability(first["name"], second["name"])
    assert reconstruction["status"] == "REAL"
    assert reconstruction["reconstructable"] is True


def test_unified_trinity_exposes_real_fusion_contract():
    system = build_default_system(fail_closed=True)
    trinity = system.components["trinity_eru"]
    assert callable(trinity.fuse_and_mirror)
    assert callable(trinity.mirror)
    assert callable(trinity.audit_mirror)
    assert callable(trinity.checkpoint)


def test_ara_self_audit_uses_real_source_when_available():
    system = build_default_system(fail_closed=True)
    report = system.components["ara_extended"].applied_to_self()
    assert report["source_status"] == "REAL"
    assert report["source_hash"]


def test_etr_decisions_expose_evidence_status():
    system = build_default_system(fail_closed=True)
    result = system.components["etr_extended"].validate_multi_framework(
        "promover autonomia comunitária com transparência"
    )
    assert result.decision_status == "APPROVED"
    assert result.evidence_sufficient is True
    assert all(a.evidence for a in result.assessments)
    proposal = system.components["etr_extended"].validate_proposal(
        "preservar autonomia e transparência",
        proposed_by="ITR",
    )
    assert "decision_status" in proposal
    assert "assessments" in proposal


def test_itr_does_not_execute_annotation_only_steps():
    system = build_default_system(fail_closed=True)
    itr = system.components["itr_extended"]
    plan = itr.generate_strategic("promover autonomia comunitária")
    all_steps = [step for phase in plan.phases for step in phase["steps"]]
    assert not (set(all_steps) & itr.ANNOTATION_ONLY_STEPS)
