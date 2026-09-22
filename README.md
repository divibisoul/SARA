# SARA — Sistema de Arquitetura Regenerativa Autônoma

**Versão:** 3.1
**Data:** 2026-09-21

## Visão Geral

SARA é um sistema de IA regenerativa e autônoma composto por 42 módulos
organizados em 8 camadas funcionais.

### Núcleo
- **ARA** — Auditoria, Regeneração, Autonomia
- **ETR** — Ética, Transparência, Responsabilidade
- **ITR** — Inovação, Tecnologia, Resiliência

### Memória
- DNA_Tags, TemporalVectorDB, RegenerativeMemory

### Segurança
- IdentityCore, EmergencyRollback, EthicalFilterChain, SafeSandbox

### Regeneração
- RegenerativeLoop, SynergyEngine

### Monitoramento
- StormMonitor, DecisionTrace, GovernanceBackend

### Pesquisa
- QuantumCrawler, NeuralLens, InnovationRadar, NeuroIntegrator, QuantumScanner

### Governança
- UbuntuEthics, BuenVivir, LegalAI, LegalCompliance, GovernedSARA

### Meta
- ARAForge, AssimilationReviewCommittee, QuantumSnapshotSystem, ERU_Engine, TransystemSARA

## Instalação

```bash
pip install -e .
```

Execução

```bash id="i0c0il"
python scripts/run_regenerative_loop.py
pytest tests/ -v
```

Ciclo Regenerativo (12 fases canônicas)

INGESTION → AUDIT → REGENERATION → IDENTITY → ETHICS →
STRATEGY → EXECUTION → VALIDATION → PERSISTENCE → SNAPSHOT →
MONITORING → GOVERNANCE

Rastreabilidade Tripla

· TemporalVectorDB: registro cronológico
· DecisionTrace: cadeia de hash verificável
· ProvenanceTracker: origem de cada regra

Módulos PENDING_INFRASTRUCTURE

8 módulos aguardam infraestrutura externa. Mantêm interface completa +
NotImplementedError descritivo. NUNCA mock.

## Serviço HTTP e Federação

O SARA também pode ser executado como serviço HTTP real sobre o mesmo runtime modular:

```bash
export SARA_API_TOKEN='<segredo>'
python -m sara.service.main
```

Endpoints protegidos:
`GET /v1/capabilities`, `POST /v1/cycle`, `POST /v1/audit`,
`POST /v1/regenerate`, `GET /v1/state`, `GET /v1/trace/{cycle_id}`.

Health:
`GET /health`.

Planta de federação: `docs/SARA_FEDERATION_BLUEPRINT.md`.

Integração N07: `SARA_SERVICE_URL`, `SARA_SERVICE_TOKEN`,
`SARA_REQUEST_TIMEOUT`.

Integração N04/N06: `SARA_BASE_URL`, `SARA_API_TOKEN`,
`SARA_ENABLE_CHAT=true`.
