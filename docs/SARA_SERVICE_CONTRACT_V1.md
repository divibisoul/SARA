# SARA — Contrato de Serviço v1

## Princípio

SARA permanece operacional como monólito modular. A fronteira HTTP é uma camada de transporte sobre o mesmo runtime; ela não cria um segundo núcleo nem duplica ARA/ETR/ITR.

## Autenticação

- `GET /health`: público para health-check.
- Demais endpoints: `Authorization: Bearer $SARA_API_TOKEN`.
- Se o token não estiver configurado, endpoints protegidos retornam `503 AUTH_NOT_CONFIGURED`.
- O token nunca deve ser enviado ao frontend/browser.

## Endpoints

### GET /health

Resposta 200:

```json
{"status":"ok","ready":true,"version":"1.0","invariants_ok":true}
```

### GET /v1/capabilities

Retorna inventário, status, dependências/capacidades registradas e módulos que ainda dependem de infraestrutura externa.

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

Retorna entradas encadeadas do DecisionTrace daquele ciclo e informa a integridade da cadeia.

## Erros

Formato único:

```json
{"error":{"code":"...","message":"...","details":{}}}
```

Códigos: `400 INVALID_JSON`, `401 UNAUTHORIZED`, `404 NOT_FOUND`, `422 INVALID_INPUT`, `503 AUTH_NOT_CONFIGURED`, `503 NOT_READY`, `500 INTERNAL_ERROR`.

## Federação

O N07 não controla a lógica interna do ciclo. Ele envia intent/execute pela fronteira de serviço e consome capabilities, health e resultados. SARA mantém autoridade sobre identidade, auditoria, regeneração, ética, estratégia, execução, validação, memória, rollback, proveniência e governança interna.

## N04/N06

Os frontends consomem principalmente `/v1/cycle`, podendo consultar `/v1/audit`, `/v1/regenerate`, `/v1/state` e `/v1/trace/{cycle_id}` conforme a função. UX, sessão, streaming de interface, documentos e apresentação permanecem nos frontends; a decisão regenerativa permanece no SARA.

## Estado de infraestrutura externa

IPFS, sandbox isolado, crawlers/scanners externos, APIs jurídicas externas e Transystem externo não são fingidos como ativos. Seus contratos permanecem no inventário e a ativação é bloqueante/explicitamente reportada quando necessária.
