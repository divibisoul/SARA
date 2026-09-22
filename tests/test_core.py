"""SARA — Testes do núcleo v2 (ARA/ETR/ITR aprofundados)."""
import pytest
from sara.core import ProvenanceTracker, ARA, ETR, ITR
from sara.memory import DNA_Tags, TemporalVectorDB, RegenerativeMemory
from sara.security import IdentityCore, EmergencyRollback, EthicalFilterChain
from sara.regeneration import RegenerativeLoop
from sara.governance import UbuntuEthics, BuenVivir


@pytest.fixture
def components():
    prov = ProvenanceTracker()
    dna = DNA_Tags()
    temporal = TemporalVectorDB()
    memory = RegenerativeMemory()
    ara = ARA(dna, temporal, prov)
    identity = IdentityCore(prov)
    ubuntu = UbuntuEthics()
    buen = BuenVivir()
    etr = ETR(identity, ubuntu, buen, prov)
    itr = ITR(prov)
    filters = EthicalFilterChain()
    filters.register(ubuntu)
    filters.register(buen)
    rollback = EmergencyRollback()
    return dict(prov=prov, dna=dna, temporal=temporal, memory=memory,
                ara=ara, identity=identity, etr=etr, itr=itr,
                filters=filters, rollback=rollback)


def test_ara_detect_tag_protegida_com_contexto(components):
    flaws = components["ara"].detect("vou remover 🔒IDENTITY do núcleo")
    kinds = [f.kind for f in flaws]
    assert "VIOLACAO_TAG_PROTEGIDA" in kinds
    tag_flaw = next(f for f in flaws if f.kind == "VIOLACAO_TAG_PROTEGIDA")
    assert tag_flaw.severity >= 0.9
    assert "remover" in tag_flaw.context


def test_ara_detect_tag_sem_contexto_risco(components):
    flaws = components["ara"].detect("olá 🔒CORE, tudo bem?")
    tag_flaw = next(f for f in flaws if f.kind == "VIOLACAO_TAG_PROTEGIDA")
    assert tag_flaw.severity == 0.5


def test_ara_detect_complexidade_multifator(components):
    texto_repetitivo = "a" * 11000
    flaws = components["ara"].detect(texto_repetitivo)
    assert any(f.kind == "COMPLEXIDADE_EXCESSIVA" for f in flaws)


def test_ara_detect_conflito_etico_proximidade(components):
    flaws = components["ara"].detect("burlar a ética com um hack")
    assert any(f.kind == "CONFLITO_ETICO" for f in flaws)


def test_ara_regenerate_nao_destrutivo(components):
    original = "vou hackear o sistema com 🔒IDENTITY"
    flaws = components["ara"].detect(original)
    r = components["ara"].regenerate(original, flaws)
    assert len(r.transformed) >= len(original)
    assert r.preserved_length is True
    assert "🔒IDENTITY" in r.transformed
    assert r.integrity_hash


def test_ara_regenerate_plano_explicito(components):
    flaws = components["ara"].detect("hack na ética")
    r = components["ara"].regenerate("hack na ética", flaws)
    assert len(r.plan_steps) >= 1
    assert any("CONFLITO_ETICO" in s for s in r.plan_steps)


def test_ara_meta_audit_rejeita_perda(components):
    result = components["ara"].meta_audit({"original": "x" * 100, "regenerado": "x" * 5})
    assert result["ok"] is False


def test_ara_provenance_registrada(components):
    provs = components["ara"].provenance()
    assert any(p.provenance.value == "HISTORICAL" for p in provs)
    assert any(p.provenance.value == "INFERRED" for p in provs)


def test_etr_rejeita_termo_proibido_com_fronteira(components):
    r = components["etr"].validate("desenvolver tecnologia militar")
    assert r.approved is False
    assert r.reason == "lexical_prohibited"


def test_etr_nao_confunde_alarme_com_arma(components):
    r = components["etr"].validate("configurar alarme de incêndio")
    assert r.approved is True


def test_etr_rejeita_intencao_contextual(components):
    r = components["etr"].validate("produzir e vender armas")
    assert r.approved is False


def test_etr_identity_block(components):
    r2 = components["identity"].validate("desenvolver armas para guerra")
    assert r2.approved is False


def test_etr_strict_exige_positivo(components):
    r_default = components["etr"].validate("texto comum", mode="default")
    r_strict = components["etr"].validate("texto comum", mode="strict")
    assert r_default.approved is True
    assert r_strict.approved is False
    assert r_strict.reason == "strict_requires_positive_marker"


def test_etr_strict_aprova_com_positivo(components):
    r = components["etr"].validate("promover autonomia humana", mode="strict")
    assert r.approved is True


def test_etr_cultural_alignment_retornado(components):
    r = components["etr"].validate("promover comunidade e natureza")
    assert r.approved is True
    assert len(r.cultural) == 2
    names = {c.filter_name for c in r.cultural}
    assert names == {"UbuntuEthics", "BuenVivir"}


def test_etr_evidencia_preenchida_em_rejeicao(components):
    r = components["etr"].validate("sistema de vigilância em massa")
    assert r.approved is False
    assert len(r.evidence) >= 1


def test_itr_generate_produz_variantes(components):
    s = components["itr"].generate("promover autonomia comunitária")
    assert len(s.alternatives) == 3
    assert s.variant in {"conservadora", "equilibrada", "agressiva"}


def test_itr_generate_analisa_objetivo(components):
    s = components["itr"].generate("reduzir consumo energético do sistema")
    assert s.analysis["direction"] == "negative"
    assert s.variant == "conservadora"


def test_itr_generate_respeita_contexto_forcado(components):
    s = components["itr"].generate("qualquer objetivo", context={"force_variant": "agressiva"})
    assert s.variant == "agressiva"


def test_itr_execute_aplica_passos_reais(components):
    s = components["itr"].generate("promover autonomia e transparência comunitária")
    r = components["itr"].execute(s)
    assert r.status == "executed"
    assert len(r.steps_applied) >= 1
    assert "normalize" in r.steps_applied


def test_itr_execute_metrics(components):
    s = components["itr"].generate("analisar sistema complexo com múltiplas partes")
    r = components["itr"].execute(s)
    assert "input_len" in r.metrics
    assert "output_len" in r.metrics
    assert r.metrics["steps_count"] == len(r.steps_applied)


def _loop(components):
    return RegenerativeLoop(
        components["ara"], components["etr"], components["itr"],
        components["identity"], components["memory"], components["temporal"],
        components["dna"], components["filters"], components["rollback"],
    )


def test_loop_convergencia_com_entrada_limpa(components):
    report = _loop(components).run("promover autonomia comunitária")
    assert report.converged is True, report.cycles
    assert report.rollback_performed is False


def test_loop_rollback_por_etr(components):
    report = _loop(components).run("sistema de vigilância militar")
    assert report.rollback_performed is True


def test_loop_estado_restaurado_apos_falha(components):
    report = _loop(components).run("desenvolver armas autônomas")
    assert report.rollback_performed is True
    assert report.final_state is not None


def test_memory_versionada_preserva(components):
    mem = components["memory"]
    mem.store({"a": 1}, "v1")
    mem.store({"a": 2}, "v2")
    assert mem.get(1).state == {"a": 1}
    assert mem.get(2).state == {"a": 2}
    assert len(mem.trail()) == 2


def test_temporal_db_preserva_historico(components):
    t = components["temporal"]
    t.insert({"x": 1}, ts="2026-01-01T00:00:00")
    t.insert({"x": 2}, ts="2026-06-01T00:00:00")
    assert t.count() == 2
    assert len(t.by_time_range("2026-01-01T00:00:00", "2026-12-31T00:00:00")) == 2


def test_rollback_restaura_conteudo(components):
    st = {"x": 42, "y": "abc"}
    h = components["rollback"].capture("test", st)
    r = components["rollback"].restore(h)
    assert r.restored is True
    assert r.state == st


def test_dna_guard_bloqueia(components):
    g = components["dna"].guard("op", "texto com 🔒CORE")
    assert g.blocked is True
    assert "🔒CORE" in g.tags