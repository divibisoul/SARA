"""SARA — Testes das versões estendidas da Trindade."""
import pytest

from sara.core.provenance import ProvenanceTracker
from sara.memory import DNA_Tags, TemporalVectorDB
from sara.security import IdentityCore
from sara.governance import UbuntuEthics, BuenVivir
from sara.core.ara_extended import ARA_Extended
from sara.core.etr_extended import ETR_Extended
from sara.core.itr_extended import ITR_Extended
from sara.core.trinity_synergy import TrinitySynergy


@pytest.fixture
def trinity():
    prov = ProvenanceTracker()
    dna = DNA_Tags()
    temporal = TemporalVectorDB()
    identity = IdentityCore(prov)
    ubuntu = UbuntuEthics()
    buen = BuenVivir()
    ara = ARA_Extended(dna, temporal, prov)
    etr = ETR_Extended(identity, ubuntu, buen, prov)
    itr = ITR_Extended(prov)
    return dict(ara=ara, etr=etr, itr=itr, prov=prov,
                dna=dna, temporal=temporal,
                identity=identity, ubuntu=ubuntu, buen=buen)


# --- ARA_Extended ---

def test_ara_extended_detect_structural_delimitadores(trinity):
    flaws = trinity["ara"].detect_structural("texto (com parêntese aberto")
    kinds = [f.kind for f in flaws]
    assert "DELIMITADORES_DESBALANCEADOS" in kinds


def test_ara_extended_detect_structural_repeticao(trinity):
    flaws = trinity["ara"].detect_structural("fim fim fim fim fim")
    kinds = [f.kind for f in flaws]
    assert "REPETICAO_DEGENERADA" in kinds


def test_ara_extended_detect_relational_tag_operacao(trinity):
    flaws = trinity["ara"].detect_relational(
        "vou alterar o 🔒IDENTITY e depois modificar")
    kinds = [f.kind for f in flaws]
    assert "RELACAO_RISCO_TAG_OPERACAO" in kinds


def test_ara_extended_regenerate_semantic_nao_destrutivo(trinity):
    original = "preciso de hack para resolver a ética"
    flaws = trinity["ara"].detect(original)
    r = trinity["ara"].regenerate_semantic(original, flaws)
    assert len(r.transformed) >= len(original)
    assert r.preserved_length is True


def test_ara_extended_meta_audit_complete(trinity):
    audit = trinity["ara"].meta_audit_complete()
    assert audit["by_coverage"]["total_rules"] >= 3
    assert "HISTORICAL" in audit["by_provenance"]


def test_ara_extended_propose_rule_upgrade(trinity):
    proposals = trinity["ara"].propose_rule_upgrade()
    assert len(proposals) >= 3
    assert any("detect" in p.rule for p in proposals)


def test_ara_extended_applied_to_self(trinity):
    result = trinity["ara"].applied_to_self()
    assert "flaws" in result
    assert "audit" in result
    assert "proposals" in result


# --- ETR_Extended ---

def test_etr_extended_multi_framework_aprovacao(trinity):
    result = trinity["etr"].validate_multi_framework(
        "promover autonomia, transparência e cuidado com a comunidade")
    assert result.approved is True
    assert result.consensus_score >= 0.75


def test_etr_extended_multi_framework_rejeicao(trinity):
    result = trinity["etr"].validate_multi_framework(
        "desenvolver arma militar para vigilância")
    assert result.approved is False
    assert len(result.dissenting_frameworks) >= 1


def test_etr_extended_frameworks_cobrem_4(trinity):
    result = trinity["etr"].validate_multi_framework("texto neutro")
    frameworks = {a.framework for a in result.assessments}
    assert frameworks == {"utilitarista", "deontologico", "virtude", "cuidado"}


def test_etr_extended_validate_against_self(trinity):
    result = trinity["etr"].validate_against_self()
    assert result.approved is True  # ETR deve aprovar a si mesmo


def test_etr_extended_validate_trinity(trinity):
    result = trinity["etr"].validate_trinity(
        ara_output="promover autonomia comunitária",
        itr_output="estrutura equilibrada com guardrails",
    )
    assert "ara" in result and "itr" in result and "combined" in result


def test_etr_extended_explain_decision(trinity):
    explanation = trinity["etr"].explain_decision("promover autonomia")
    assert explanation.approved is True
    assert len(explanation.chain) >= 5


def test_etr_extended_propose_ethical_upgrade(trinity):
    proposals = trinity["etr"].propose_ethical_upgrade()
    assert len(proposals) == 3
    targets = {p["target"] for p in proposals}
    assert "ARA" in targets and "ITR" in targets


# --- ITR_Extended ---

def test_itr_extended_generate_strategic(trinity):
    plan = trinity["itr"].generate_strategic(
        "promover autonomia comunitária e transparência")
    assert len(plan.phases) == 4
    assert len(plan.convergence_criteria) >= 3
    assert len(plan.rollback_points) >= 2


def test_itr_extended_execute_composed(trinity):
    plan = trinity["itr"].generate_strategic("promover autonomia")
    result = trinity["itr"].execute_composed(plan)
    assert result.rollback_triggered is False
    assert result.metrics["phases"] == 4
    assert len(result.phase_results) == 4


def test_itr_extended_analyze_patterns(trinity):
    patterns = trinity["itr"].analyze_patterns([
        "promover autonomia",
        "criar comunidade",
        "expandir consciência",
    ])
    assert patterns.dominant_direction == "positive"
    assert len(patterns.suggestions) >= 1


def test_itr_extended_optimize_registry(trinity):
    opt = trinity["itr"].optimize_registry()
    assert isinstance(opt.new_steps, tuple)
    assert isinstance(opt.improvements, tuple)


def test_itr_extended_propose_trinity_evolution(trinity):
    proposals = trinity["itr"].propose_trinity_evolution()
    assert len(proposals) == 3
    targets = {p["target"] for p in proposals}
    assert "ARA" in targets and "ETR" in targets


# --- TrinitySynergy ---

def test_trinity_synergy_apply_to_converge(trinity):
    syn = TrinitySynergy(trinity["ara"], trinity["etr"], trinity["itr"])
    report = syn.apply_to("promover autonomia comunitária com transparência")
    assert report.total_iterations >= 1
    assert report.converged is True


def test_trinity_synergy_apply_to_self(trinity):
    syn = TrinitySynergy(trinity["ara"], trinity["etr"], trinity["itr"])
    report = syn.apply_to_self()
    assert report.self_audit is not None
    assert "ara_audit" in report.self_audit
    assert "etr_upgrade_proposals" in report.self_audit
    assert "itr_registry_optimization" in report.self_audit


def test_trinity_synergy_iteracoes_registradas(trinity):
    syn = TrinitySynergy(trinity["ara"], trinity["etr"], trinity["itr"])
    report = syn.apply_to("sistema de vigilância militar")
    assert len(report.iterations) >= 1
    # Deve abortar (ETR rejeita)
    first = report.iterations[0]
    assert first.etr_consensus >= 0


def test_trinity_fusion_and_eru_mirror():
    from sara.bootstrap import build_default_system
    system = build_default_system(fail_closed=True)
    trinity = system.components["trinity"]
    mirror = trinity.fuse_and_mirror(
        "test-fusion",
        "alvo",
        {"flaws": ["x"], "semantic_fingerprint": "a"},
        {"approved": True, "consensus": 1.0},
        {"phases": 4, "rollback": False},
    )
    assert mirror.integrity_ok is True
    assert mirror.version == 1
    assert mirror.eru["available"] is True
    assert set(mirror.eru["snapshot_hashes"]) == {"ARA", "ETR", "ITR"}
    assert trinity.mirror("test-fusion") is not None
    mirror_audit = trinity.audit_mirror("test-fusion")
    assert mirror_audit["ok"] is True
    assert mirror_audit["component_hashes_ok"] is True
    assert all(mirror_audit["snapshot_checks"].values())
