"""Coverage for the shared semantic layer and ARA/ETR/ITR coupling."""
from sara.core.provenance import ProvenanceTracker
from sara.core.semantic_engine import SemanticEngine
from sara.core.ara_extended import ARA_Extended
from sara.core.etr_extended import ETR_Extended
from sara.core.itr_extended import ITR_Extended
from sara.memory import DNA_Tags, TemporalVectorDB
from sara.security import IdentityCore
from sara.governance import UbuntuEthics, BuenVivir


def _components():
    prov = ProvenanceTracker()
    dna = DNA_Tags()
    temporal = TemporalVectorDB()
    identity = IdentityCore(prov)
    ubuntu = UbuntuEthics()
    buen = BuenVivir()
    return {
        "semantic": SemanticEngine(),
        "ara": ARA_Extended(dna, temporal, prov),
        "etr": ETR_Extended(identity, ubuntu, buen, prov),
        "itr": ITR_Extended(prov),
    }


def test_semantic_engine_produces_stable_structured_frame():
    engine = SemanticEngine()
    frame = engine.analyze("SARA deve preservar a identidade e validar o resultado.")
    assert frame.text_length > 0
    assert frame.relations
    assert frame.fingerprint == engine.analyze(
        "SARA deve preservar a identidade e validar o resultado."
    ).fingerprint


def test_ara_exposes_semantic_findings_additively():
    ara = _components()["ara"]
    flaws = ara.detect_semantic("vou remover identidade do sistema")
    assert any(f.kind == "RELACAO_ACAO_DESTRUTIVA" for f in flaws)


def test_etr_validates_semantic_transformation():
    etr = _components()["etr"]
    result = etr.validate_transformation(
        "preservar autonomia e validar resultado",
        "preservar autonomia e validar resultado com rastreabilidade",
    )
    assert result["ok"] is True


def test_itr_strategy_contains_semantic_profile():
    itr = _components()["itr"]
    plan = itr.generate_strategic("preservar autonomia e validar resultado")
    extract_phase = next(p for p in plan.phases if p["name"] == "extract")
    assert "semantic_profile" in extract_phase
    assert extract_phase["semantic_profile"]["relation_count"] >= 1


def test_itr_composed_execution_records_semantic_guard():
    itr = _components()["itr"]
    plan = itr.generate_strategic("preservar autonomia e validar resultado")
    result = itr.execute_composed(plan)
    assert result.metrics["semantic_guard_passed"] is True
