from datetime import datetime, timezone

from sara.bootstrap import build_default_system


def finding(required_property: str = "preservar e validar antes de executar") -> dict:
    return {
        "schema_version": "1.0.0",
        "finding_id": "trinity-rgo-test-1",
        "object_id": "object-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": "corr-trinity-1",
        "trace_id": "trace-trinity-1",
        "source": {"system": "BugShield", "module": "Scanner", "version": "1.2.0"},
        "epistemic": {"mode": "INSPECTION", "verification_state": "VERIFIED"},
        "actionability": {"status": "ACTIONABLE"},
        "failure": {
            "type": "BUG",
            "description": "preservar e validar dados com transparencia, autonomia, cuidado e comunidade",
            "nature": "validation",
        },
        "correction_boundary": {
            "problem_to_resolve": "prevenir execução sem validação",
            "required_property": required_property,
        },
        "dual": {"status": "UNRESOLVED"},
        "evidence": [{"id": "ev-trinity-1", "kind": "test", "ref": "test://trinity-rgo"}],
        "provenance": {"origin": "test", "input_hash": "sha256:trinity-input"},
    }


def test_rgo_trinity_stage_inheritance_and_mmd():
    system = build_default_system()
    result = system.components["trinity_rgo"].process(finding(), cycle_id="cycle-trinity-1")

    assert result.final_status == "VALIDATED"
    assert result.mmd_state == "MACRO"
    assert len(result.stages) >= 6

    for previous, current in zip(result.stages, result.stages[1:]):
        assert current.parent_hash == previous.output_hash
        assert current.input_hash == previous.output_hash

    state = system.components["rgo"].state()
    assert state.accepted >= 1
    assert state.integrity
    assert system.components["mmd"].state == "MACRO"


def test_detection_only_finding_stays_unresolved_but_pipeline_remains_traceable():
    system = build_default_system()
    result = system.components["trinity_rgo"].process(finding(required_property=""), cycle_id="cycle-trinity-2")
    assert result.rgo_record["dual"]["status"] == "UNRESOLVED"
    assert result.final_status == "VALIDATED"
    assert all(stage.output_hash.startswith("sha256:") for stage in result.stages)
    assert all(len(stage.eru_snapshot_hash) == 64 for stage in result.stages)
    assert all(all(ch in "0123456789abcdef" for ch in stage.eru_snapshot_hash) for stage in result.stages)
    assert all(len(stage.rgo_evidence_chain_hash) == 64 for stage in result.stages)
    assert all(all(ch in "0123456789abcdef" for ch in stage.rgo_evidence_chain_hash) for stage in result.stages)
    assert [s.sequence_index for s in result.stages] == list(range(1, len(result.stages) + 1))
    assert system.components["rgo"].stage_evidence_count() == len(result.stages)
    assert system.components["rgo"].stage_evidence_integrity()
