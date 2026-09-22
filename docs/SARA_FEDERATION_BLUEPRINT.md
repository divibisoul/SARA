# SARA — Planta Técnica de Federação e Integração

## 1. Papel

O SARA é o núcleo regenerativo especializado do SOUL. Ele mantém autoridade sobre:
- auditoria e detecção;
- ética e validação;
- estratégia e transformação;
- ciclo regenerativo;
- memória, proveniência, rollback e evidência;
- governança interna do próprio SARA.

O N07 (Orquestrador-) mantém autoridade sobre:
- descoberta;
- roteamento;
- execução federada;
- correlação distribuída;
- mesh SOUL;
- recursos neurais/compute/SuperGPU.

O SARA não substitui o N07 e não cria um novo núcleo N08.

## 2. Arquitetura interna

Camadas existentes preservadas:
- núcleo: ARA, ETR, ITR, SistemaVivo, TrinitySynergy;
- memória: DNA_Tags, TemporalVectorDB, RegenerativeMemory;
- segurança: IdentityCore, EmergencyRollback, EthicalFilterChain, SafeSandbox;
- regeneração: RegenerativeLoop, SynergyEngine, RegenerativeState;
- monitoramento: StormMonitor, DecisionTrace, GovernanceBackend, ExecutionReport;
- pesquisa: QuantumCrawler, NeuralLens, InnovationRadar, NeuroIntegrator, QuantumScanner;
- governança: UbuntuEthics, BuenVivir, LegalAI, LegalCompliance, GovernedSARA;
- meta: ARAForge, AssimilationReviewCommittee, QuantumSnapshotSystem, ERU_Engine, TransystemSARA;
- auditoria: CycleAuditor;
- contratos: SaraModule, ModuleRegistry, CycleContext, CyclePhase, InvariantValidator;
- integração: ConnectedRuntime.

## 3. Fluxo canônico

1. INGESTION — DNA_Tags preserva identidade, tags e bloqueios.
2. AUDIT — ARA lexical + estrutural + relacional.
3. REGENERATION — ARA transforma de forma não destrutiva e registra integridade.
4. IDENTITY — IdentityCore valida fronteiras e identidade.
5. ETHICS — ETR + frameworks éticos validam.
6. STRATEGY — ITR gera plano e critérios.
7. EXECUTION — ITR executa operações registradas.
8. VALIDATION — ETR revalida o estado resultante.
9. PERSISTENCE — TemporalVectorDB + RegenerativeMemory + ERU registram estado.
10. SNAPSHOT — EmergencyRollback/QuantumSnapshot capturam ponto restaurável.
11. MONITORING — DecisionTrace + monitoramento e relatório.
12. GOVERNANCE — governança, compliance e pesquisa são observados sem fingir infraestrutura externa.

Convergência ocorre apenas quando invariantes, ética, ausência de falhas residuais e execução válida são satisfeitas. Caso contrário, um novo ciclo é tentado até o limite; então rollback é executado.

## 4. Invariantes

Antes de executar:
- registry não vazio;
- metadados completos;
- dependências resolvidas;
- grafo acíclico;
- fases válidas;
- contexto de ciclo válido;
- DecisionTrace íntegro.

Depois:
- ordem das fases monotônica;
- falha exige abort ou classificação não bloqueante explícita;
- execução exige persistência e snapshot;
- abort exige motivo;
- evidência de execução precisa permanecer rastreável.

## 5. Contrato HTTP do SARA

Base: `/v1`.

### GET /health

Sem autenticação para health check básico.

Resposta:
```json
{
  "status": "ok",
  "ready": true,
  "version": "3.1.0",
  "protocol": "sara-http/1",
  "invariants_ok": true,
  "trace_integrity": true,
  "module_count": 0,
  "pending_infrastructure": []
}
```

### GET /v1/capabilities

Bearer obrigatório.

Retorna operações versionadas:
- sara.cycle@1.0.0
- sara.audit@1.0.0
- sara.regenerate@1.0.0
- sara.state@1.0.0
- sara.trace@1.0.0

### POST /v1/cycle

Request:
```json
{
  "input": "texto",
  "cycle_id": "correlation-opcional"
}
```

Response contém:
- cycle_id;
- estado final;
- converged;
- rollback_performed;
- execution_report;
- trace_hash;
- snapshots/steps/invariants registrados pelo runtime.

### POST /v1/audit

Request:
```json
{"input":"texto"}
```

Resposta contém falhas lexical/estrutural/relacional, validação ETR e proveniência.

### POST /v1/regenerate

Request:
```json
{"input":"texto"}
```

Resposta contém original, transformed, regras, plano, integridade e validação ética.

### GET /v1/state

Retorna estado vivo, histórico, trace, registry e proveniência.

### GET /v1/trace/{cycle_id}

Retorna entradas do DecisionTrace da correlação solicitada e a integridade da cadeia.

### Erros

Formato:
```json
{
  "error": {
    "code": "SARA_CODE",
    "message": "descrição",
    "details": {}
  }
}
```

Códigos estruturais: UNAUTHORIZED, AUTH_NOT_CONFIGURED, INVALID_JSON, INVALID_INPUT, NOT_READY, NOT_FOUND, INTERNAL_ERROR.

## 6. Integração N07

O N07 chama o SARA por HTTP usando:
- `SARA_SERVICE_URL`;
- `SARA_SERVICE_TOKEN`;
- timeout configurável em `SARA_REQUEST_TIMEOUT`.

Operações N07:
- sara.cycle@1.0.0
- sara.audit@1.0.0
- sara.regenerate@1.0.0
- sara.state@1.0.0
- sara.capabilities@1.0.0

O resultado estruturado completo do SARA é preservado em `Result.Metadata["sara_result_json"]` no N07 e propagado no gateway Mesh.

O gateway Mesh aceita payload estruturado para capacidades `sara.*`, sem alterar o contrato numérico das capacidades neurais/compute existentes.

## 7. Integração N04 e N06

N04 e N06 possuem clientes HTTP independentes para SARA.

Variáveis:
- `SARA_BASE_URL`
- `SARA_API_TOKEN`
- `SARA_ENABLE_CHAT=true`

Quando habilitado, o fluxo de conversa envia a entrada textual ao `/v1/cycle`. A saída real do SARA é anexada ao contexto do modelo, preservando o streaming existente dos frontends.

Sem `SARA_ENABLE_CHAT=true`, a integração não é considerada ativa e nenhum resultado falso é produzido.

## 8. Autenticação

- SARA HTTP: Bearer token em todos os endpoints `/v1`.
- N07 -> SARA: `SARA_SERVICE_TOKEN` no servidor.
- N04/N06 -> SARA: `SARA_API_TOKEN` somente no ambiente server-side.
- Nenhum segredo deve ser commitado.
- O Mesh SOUL continua usando seu contrato/HMAC existente entre os núcleos SOUL.

## 9. Infraestrutura futura

Módulos externos continuam com interface completa e status explícito:
SafeSandbox, QuantumCrawler, QuantumScanner, LegalAI patent oracle, DecisionTrace IPFS, TransystemSARA e GovernanceBackend UI.

A ativação exige backend/credencial real e revalidação de invariantes. Não há caminho de “modo simulado”.

## 10. Evolução de implantação

Fase 1: monólito modular Python.
Fase 2: serviço HTTP SARA.
Fase 3: N07 + N04 + N06 conectados.
Fase 4: persistência externa e observabilidade distribuída.
Fase 5: extração de bounded contexts somente quando métricas de carga, isolamento ou disponibilidade justificarem.
