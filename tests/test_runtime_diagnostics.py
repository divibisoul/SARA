"""Diagnóstico de runtime para regressões do núcleo."""

from sara.bootstrap import build_default_system


def test_runtime_diagnostics_for_clean_cycle_and_complexity_detector():
    system = build_default_system(fail_closed=True)
    ara = system.components["ara"]
    text = "a" * 11000
    n = len(text)
    unique_ratio = len(set(text)) / n
    avg_sentence = n
    score = (0.4 if n > ara.COMPLEXITY_MAX_LEN else 0.0)
    score += 0.3 if unique_ratio < ara.COMPLEXITY_MIN_UNIQUE_RATIO else 0.0
    score += 0.2 if avg_sentence > ara.COMPLEXITY_MAX_AVG_SENTENCE else 0.0
    flaws = ara.detect(text)
    assert score + 1e-12 >= ara.COMPLEXITY_SCORE_THRESHOLD, (
        f"score={score!r}; threshold={ara.COMPLEXITY_SCORE_THRESHOLD!r}"
    )
    assert any(f.kind == "COMPLEXIDADE_EXCESSIVA" for f in flaws), (
        f"score={score!r}; threshold={ara.COMPLEXITY_SCORE_THRESHOLD!r}; flaws={flaws!r}"
    )

    itr = system.components["itr_extended"]
    assert type(system.components["loop"]._itr).__name__ == "ITR_Extended"
    try:
        plan = itr.generate_strategic(
            "promover autonomia comunitária",
            {"cycle": 1, "ara_audit": {"flaws": [], "semantic_fingerprint": "x"}},
        )
    except Exception as exc:
        raise AssertionError(f"STRATEGY direct failure: {type(exc).__name__}: {exc}") from exc
    assert len(plan.phases) == 4

    etr = system.components["etr_extended"]
    ethical = etr.validate_multi_framework("promover autonomia comunitária")
    assert ethical.approved is True, ethical

    result = system.sistema_vivo.process("promover autonomia comunitária", cycle_id="diagnostic-clean-001")
    assert result.loop_report.converged is True, result.loop_report.cycles
    assert result.loop_report.fusion is not None, result.loop_report.cycles



def test_runtime_diagnostic_execution_failure_is_explicit():
    import json
    system = build_default_system(fail_closed=True)
    itr = system.components["itr_extended"]
    plan = itr.generate_strategic("promover autonomia comunitária", {"cycle": 1, "ara_audit": {"flaws": []}})
    composed = itr.execute_composed(plan)
    assert composed.rollback_triggered is False, json.dumps(composed.phase_results, ensure_ascii=False, default=str)

    result = system.sistema_vivo.process("promover autonomia comunitária", cycle_id="diagnostic-execution-001")
    if not result.loop_report.converged:
        assert result.loop_report.cycles, "ciclo sem evidência"
        cycle = result.loop_report.cycles[-1]
        assert "execution" in cycle["phases"], json.dumps(cycle, ensure_ascii=False, default=str)



def test_runtime_diagnostic_itr_extended_consciousness_path():
    import json
    system = build_default_system(fail_closed=True)
    itr = system.components["itr_extended"]
    plan = itr.generate_strategic(
        "promover consciência comunitária",
        {"cycle": 1, "ara_audit": {"flaws": []}},
    )
    composed = itr.execute_composed(plan)
    assert composed.rollback_triggered is False, json.dumps(composed.phase_results, ensure_ascii=False, default=str)



def test_runtime_diagnostic_autonomy_phase_boundary():
    import json
    system = build_default_system(fail_closed=True)
    result = system.sistema_vivo.process("promover autonomia comunitária", cycle_id="diagnostic-phase-001")
    cycle = result.loop_report.cycles[-1]
    expected = [
        "ingestion", "audit", "regeneration", "identity", "ethics",
        "strategy", "execution", "validation", "persistence",
        "snapshot", "monitoring", "governance",
    ]
    assert all(p in cycle["phases"] for p in expected), json.dumps(cycle, ensure_ascii=False, default=str)
