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

Backends externos continuam sendo ativados por detecção/configuração real. Quando a infraestrutura necessária não existe, a capacidade permanece exposta com estado explícito e erro operacional determinístico; nunca há mock ou sucesso fabricado.


## Serviço HTTP e Federação

O SARA também pode ser executado como serviço HTTP real sobre o mesmo runtime modular:

```bash
export SARA_API_TOKEN='<segredo>'
python -m sara.service.main
```

Endpoints protegidos:
`GET /v1/capabilities`, `POST /v1/cycle`, `POST /v1/audit`,
`POST /v1/regenerate`, `GET /v1/state`, `GET /v1/trace/{cycle_id}`, `GET /v1/governance/ui`.

Health:
`GET /health`.

Planta de federação: `docs/SARA_FEDERATION_BLUEPRINT.md`.

Integração N07: `SARA_SERVICE_URL`, `SARA_SERVICE_TOKEN`,
`SARA_REQUEST_TIMEOUT`.

Integração N04/N06: `SARA_BASE_URL`, `SARA_API_TOKEN`,
`SARA_ENABLE_CHAT=true`.

## Octacore — G0 SARA kernel

Octacore is the SOUL/SARA **system GPU**: a federated software execution processor over eight domain slots G0–G7. It is **not a silicon octa-core CPU** and does not imply CUDA, NPU or physical GPU hardware.

SARA is G0 and remains the sole regenerative authority. Octacore exposes the existing SARA operations `sara.cycle`, `sara.audit`, `sara.regenerate`, `sara.state` and `sara.trace` as a kernel boundary without duplicating ARA/ETR/ITR or the regenerative loop.

VagusBus remains the control plane. The new `POST /v1/vagus` boundary feeds the **existing** VagusNerveBus; it does not create a second event bus.
