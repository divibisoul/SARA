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
    assert score >= ara.COMPLEXITY_SCORE_THRESHOLD, (
        f"score={score!r}; threshold={ara.COMPLEXITY_SCORE_THRESHOLD!r}"
    )
    assert any(f.kind == "COMPLEXIDADE_EXCESSIVA" for f in flaws), (
        f"score={score!r}; threshold={ara.COMPLEXITY_SCORE_THRESHOLD!r}; flaws={flaws!r}"
    )

    result = system.sistema_vivo.process("promover autonomia comunitária", cycle_id="diagnostic-clean-001")
    assert result.loop_report.converged is True, result.loop_report.cycles
    assert result.loop_report.fusion is not None, result.loop_report.cycles
