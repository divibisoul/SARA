# SARA — Contrato de Serviço v1

## Princípio

SARA permanece operacional como monólito modular. A fronteira HTTP é uma camada de transporte sobre o mesmo runtime; ela não cria um segundo núcleo nem duplica ARA/ETR/ITR.

## Autenticação

- `GET /health`: público para health-check.
- Demais endpoints: `Authorization: Bearer $SARA_API_TOKEN`.
- Se o token não estiver configurado ou for inválido, endpoints protegidos permanecem fechados e retornam `401 UNAUTHORIZED`.
- O token nunca deve ser enviado ao frontend/browser.

## Endpoints

### GET /health

Resposta 200:

```json
{"status":"ok","ready":true,"version":"3.1.0","protocol":"sara-http/1","invariants_ok":true,"trace_integrity":true,"provenance_integrity":true,"rollback_chain_integrity":true}
```

### GET /v1/capabilities

Retorna identidade federativa, operações versionadas, capability descriptors,
inventário, status, dependências e módulos que ainda dependem de infraestrutura externa.

Operações:
- `sara.cycle@1.0.0`
- `sara.audit@1.0.0`
- `sara.regenerate@1.0.0`
- `sara.state@1.0.0`
- `sara.trace@1.0.0`
- `sara.hortacore.assess@1.0.0`

### POST /v1/hortacore/assess

Request:

```json
{"proposal":{"name":"nome","description":"proposta a avaliar","license":"MIT"}}
```

Executa o método real `AeternumChimeraBridge.fuse_assessment()`. A avaliação passa por
`GovernedSARA` e pelo snapshot reversível do `ERU_Engine`; o estado de compute quântico
continua explicitamente `BLOCKED_INFRASTRUCTURE` quando não houver backend verificado.

### POST /v1/cycle

Request:

```json
{"input":"texto a processar","cycle_id":"opcional-id"}
```

Executa o ciclo regenerativo completo no runtime real e retorna convergência, rollback, estado final, evidência e hash de trace.

### POST /v1/audit

Request:

```json
{"input":"texto a auditar"}
```

Executa ARA Extended nas camadas lexical, estrutural e relacional e devolve evidências das falhas encontradas.

### POST /v1/regenerate

Request:

```json
{"input":"texto a regenerar"}
```

Executa a regeneração semântica real do ARA Extended e retorna regras aplicadas e hash de integridade.

### GET /v1/state

Retorna estado observável do SistemaVivo, histórico, trace, registry e proveniência disponível.

### GET /v1/trace/{cycle_id}

Retorna entradas encadeadas do DecisionTrace daquele ciclo, registros temporais relacionados e integridade de trace/proveniência.

## Contexto probabilístico opcional

`POST /v1/cycle` e `POST /v1/audit` aceitam `context` sem alterar o contrato
existente. Quando `PROBABILISTIC_LAYER=true`, o bloco
`context.probabilistic` é validado pelo `ProbabilisticReasoningLayer`.

O bloco pode conter nós discretos com `states`, `prior`, `prior_type`,
`pseudo_counts`, `evidence`, `posterior`, `dirichlet_posterior`,
`neural_posterior`, `confidence`, `entropy`, `source` e `provenance`,
estrutura DAG e referências de intervenção.

Defaults: `pseudo_counts=1.0`, `alpha_dirichlet=0.5`,
`beta_neural=0.5`, `temperature=1.0`.

A camada neural é determinística no ciclo e não treina pesos online. O SARA
continua sendo a autoridade ARA/ETR/ITR; Bayes/neural somente enriquecem contexto,
auditoria, monitoramento e evidência.

## Erros

Formato único:

```json
{"error":{"code":"...","message":"...","details":{}}}
```

Códigos: `400 INVALID_JSON`, `401 UNAUTHORIZED`, `404 NOT_FOUND`, `422 INVALID_INPUT`, `503 AUTH_NOT_CONFIGURED`, `503 NOT_READY`, `500 INTERNAL_ERROR`.

## Federação

O N07 não controla a lógica interna do ciclo. Ele envia intent/execute pela fronteira de serviço e consome capabilities, health e resultados. `correlationId` / `X-Correlation-ID` é preservado quando fornecido. SARA mantém autoridade sobre identidade, auditoria, regeneração, ética, estratégia, execução, validação, memória, rollback, proveniência e governança interna.

## N04/N06

Os frontends consomem principalmente `/v1/cycle`, podendo consultar `/v1/audit`, `/v1/regenerate`, `/v1/state` e `/v1/trace/{cycle_id}` conforme a função. UX, sessão, streaming de interface, documentos e apresentação permanecem nos frontends; a decisão regenerativa permanece no SARA.

## Estado de infraestrutura externa

IPFS, sandbox isolado, crawlers/scanners externos, APIs jurídicas externas e Transystem externo não são fingidos como ativos. Seus contratos permanecem no inventário e a ativação é bloqueante/explicitamente reportada quando necessária.

## Topologia federada e nomes legados

A auditoria do código atual não encontrou módulos executáveis com os nomes literais
`OctaCore` ou `Nervobus`. Para preservar a intenção sem inventar infraestrutura,
a equivalência operacional é:

- **OctaCore**: topologia lógica de oito autoridades, formada por N01–N07 + SARA.
  N07 permanece dono da orquestração/federação/compute SuperGPU; SARA permanece dono
  da regeneração, auditoria, ética, memória, proveniência e governança interna.
- **Nervobus**: função de barramento/fabric já realizada pelo **Soul Mesh**, com
  descoberta, correlação, autenticação HMAC e anti-replay; não é um segundo transporte.
- **HortaCore**: ponte meta real `AeternumChimeraBridge`, registrada no bootstrap SARA.
  A operação federada `sara.hortacore.assess@1.0.0` chama o
  `fuse_assessment()` existente e preserva GovernedSARA + ERU_Engine como autoridades.
- **SuperGPU + Orquestrador**: continuam centralizados no N07. N02/N03/N04 possuem
  apenas adaptadores de chamada pelo Soul Mesh; não criam um quarto executor de compute.
