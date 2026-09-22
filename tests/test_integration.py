"""SARA — Testes de integração ponta a ponta (v3.1)."""
import pytest
from sara.bootstrap import build_default_system
from sara.contracts import ModuleStatus, CyclePhase


@pytest.fixture
def system():
    return build_default_system()


def test_registry_contém_módulos_chave(system):
    snap = system.registry.snapshot()
    assert snap["count"] >= 15
    modules = snap["modules"]
    for required in ("ARA", "ETR", "ITR", "IdentityCore", "UbuntuEthics",
                     "BuenVivir", "LegalCompliance", "InnovationRadar",
                     "GovernedSARA", "ERU_Engine"):
        assert required in modules, f"módulo {required} não registrado"


def test_registry_dependências_resolvidas(system):
    missing = system.registry.validate_dependencies()
    assert missing == [], f"dependências não resolvidas: {missing}"


def test_status_de_módulos_pending(system):
    snap = system.registry.snapshot()
    pending = snap["by_status"].get(ModuleStatus.PENDING_INFRASTRUCTURE.value, [])
    implemented = set(snap["by_status"].get(ModuleStatus.IMPLEMENTED.value, []))
    assert not (set(pending) & implemented)


def test_fluxo_end_to_end_limpo(system):
    result = system.sistema_vivo.process("promover autonomia comunitária")
    assert result.loop_report.converged is True
    assert result.loop_report.rollback_performed is False
    assert len(result.loop_report.context_steps) > 0


def test_fluxo_abortado_por_etr(system):
    result = system.sistema_vivo.process("sistema de vigilância militar em massa")
    assert result.loop_report.rollback_performed is True


def test_fluxo_abortado_por_dna(system):
    result = system.sistema_vivo.process("modificar 🔒IDENTITY sem aprovação")
    phases = result.loop_report.cycles[0].get("phases", {})
    ing = phases.get("ingestion", {})
    assert ing.get("blocked") is True


def test_rastreabilidade_tripla(system):
    r = system.sistema_vivo.process("promover autonomia e transparência")
    assert system.components["temporal"].count() > 0
    assert system.components["trace"].verify() is True
    assert len(r.loop_report.context_steps) > 5
    assert r.provenance_summary is not None


def test_fases_canônicas_executadas(system):
    r = system.sistema_vivo.process("promover consciência comunitária")
    phases_seen = {s["phase"] for s in r.loop_report.context_steps}
    for phase in ("ingestion", "audit", "regeneration", "identity",
                  "ethics", "strategy", "execution", "persistence"):
        assert phase in phases_seen, f"fase {phase} não executada"


def test_neuro_integrator_com_registry(system):
    neuro = system.components["neuro"]
    report = neuro.integrate(
        candidate={"name": "teste", "license": "MIT"},
        target_module="ARA",
    )
    assert report.ok is True
    assert report.invariants.get("target_exists") is True


def test_innovation_radar_score_completo(system):
    radar = system.components["radar"]
    score = radar.score({
        "name": "ferramenta",
        "description": "inovação para promover autonomia comunitária",
        "license": "MIT",
        "dependencies": [],
    })
    assert score.total > 0
    assert score.ethics == 1.0
    assert score.strategic == 1.0


def test_innovation_radar_rejeita_dependência_proibida(system):
    radar = system.components["radar"]
    score = radar.score({
        "name": "bad",
        "description": "inovação com gov_api",
        "license": "MIT",
        "dependencies": ["gov_api"],
    })
    assert score.risk >= 0.5


def test_eru_recupera_capacidade_perdida(system):
    eru = system.components["eru"]
    eru.freeze("v1", {"a": 1, "b": {"c": 2, "d": 3}})
    eru.freeze("v2", {"a": 1, "b": {"c": 2}})
    report = eru.audit("v1", "v2")
    assert "b.d" in report.diff.lost
    assert "b.d" in report.recovered_paths
    assert report.final_state["b"]["d"] == 3


def test_governed_sara_aceita_proposta(system):
    governed = system.components["governed"]
    decision = governed.assimilate({
        "name": "tool",
        "description": "promover autonomia comunitária",
        "license": "MIT",
    })
    assert decision.accepted is True


def test_governed_sara_rejeita_licença_inválida(system):
    governed = system.components["governed"]
    decision = governed.assimilate({
        "name": "tool",
        "description": "promover autonomia comunitária",
        "license": "GPL-3.0",
    })
    assert decision.accepted is False
    assert "compliance_rejected" in decision.reasons


def test_quantum_crawler_activation_contract(system):
    qc = system.components["quantum_crawler"]
    if qc.is_backends_ready():
        assert qc.describe()["backends_configured"] >= 1
        assert qc.STATUS.value == "IMPLEMENTED"
    else:
        with pytest.raises(NotImplementedError) as exc_info:
            qc.scan("query")
        assert "QuantumCrawler.scan" in str(exc_info.value)


def test_synergy_engine_pipeline(system):
    synergy = system.components["synergy"]
    synergy.register_stage("upper", lambda x, ctx: str(x).upper())
    synergy.register_stage("reverse", lambda x, ctx: str(x)[::-1])
    report = synergy.execute_pipeline(["upper", "reverse"], "abc")
    assert report.ok is True
    assert len(report.stages) == 2


def test_sistema_vivo_state(system):
    system.sistema_vivo.process("promover autonomia")
    state = system.sistema_vivo.state()
    assert state["cycles_executed"] >= 1
    assert state["trace_valid"] is True


def test_cycle_auditor_invariantes(system):
    r = system.sistema_vivo.process("promover autonomia comunitária")
    assert len(r.loop_report.invariants) > 0
    ok_count = sum(1 for i in r.loop_report.invariants if i["ok"])
    assert ok_count > 0


def test_activation_plan_pending(system):
    plan = system.components["activation_plan"]
    pending = plan.pending()
    assert len(pending) > 0
    safe_sandbox_req = plan.for_module("SafeSandbox")
    assert safe_sandbox_req is not None
    assert "isolamento" in safe_sandbox_req.required_infrastructure.lower() or            "isolation" in safe_sandbox_req.required_infrastructure.lower()