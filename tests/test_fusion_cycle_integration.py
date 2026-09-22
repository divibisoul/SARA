"""SARA — integração do espelho de fusão dentro do ciclo regenerativo."""

from sara.bootstrap import build_default_system


def test_fusion_mirror_is_first_class_cycle_state():
    system = build_default_system(fail_closed=True)
    result = system.sistema_vivo.process(
        "preservar autonomia comunitária com transparência",
        cycle_id="cycle-fusion-runtime-001",
    )

    fusion = result.loop_report.fusion
    assert fusion is not None
    assert fusion["cycle_id"] == "cycle-fusion-runtime-001"
    assert fusion["version"] >= 1
    assert fusion["integrity_ok"] is True
    assert fusion["fused_hash"]
    assert fusion["ara_hash"]
    assert fusion["etr_hash"]
    assert fusion["itr_hash"]
    assert fusion["eru_snapshot_hashes"]
    assert fusion["fusion_snapshot_hash"]

    checks = {item["name"]: item for item in result.loop_report.invariants}
    assert checks["fusion_cycle_identity"]["ok"] is True
    assert checks["fusion_target_hash_matches_context"]["ok"] is True
    assert checks["fusion_component_hashes_present"]["ok"] is True
    assert checks["fusion_integrity_ok"]["ok"] is True

    mirror = system.components["trinity"].mirror(
        "cycle-fusion-runtime-001", version=fusion["version"]
    )
    assert mirror is not None
    audit = system.components["trinity"].audit_mirror(
        "cycle-fusion-runtime-001", version=fusion["version"]
    )
    assert audit["ok"] is True
    assert audit["component_hashes_ok"] is True
    assert all(audit["snapshot_checks"].values())
