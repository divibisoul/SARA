from sara.audit.engineering_matrix import EngineeringMatrix, REAL, PARTIAL, BLOCKED, UNMEASURABLE


def test_engineering_matrix_is_executable_and_conservative():
    report = EngineeringMatrix().audit()
    assert report.totals[REAL] > 0
    assert report.totals[BLOCKED] >= 1
    assert report.status == PARTIAL
    assert len(report.items) >= 100
    assert report.integrity_hash and len(report.integrity_hash) == 64


def test_engineering_matrix_does_not_mark_unproven_federation_real():
    report = EngineeringMatrix().audit()
    items = {item.requirement: item.status for item in report.items}
    assert items["N07 intent/execute/resultado/health/trace"] == UNMEASURABLE
    assert items["N04 mensagem/contexto/result/cycle_id/errors"] == UNMEASURABLE
    assert items["N06 mensagem/contexto/result/cycle_id/errors"] == UNMEASURABLE
