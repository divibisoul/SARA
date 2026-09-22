# SARA — Ativação de Produção

## 1. SARA standalone

No ambiente do host:

SARA_API_TOKEN=<segredo>

SARA_HOST=0.0.0.0
SARA_PORT=8090

Executar:

python -m sara.service.main

Validar:

GET /health
GET /v1/capabilities com Authorization: Bearer <token>

## 2. SARA via container

Defina SARA_API_TOKEN no ambiente e execute:

docker compose -f deploy/docker-compose.yml up --build

O healthcheck do container consulta /health.

## 3. N07

No servidor N07:

SARA_SERVICE_URL=http://<host-sara>:8090
SARA_SERVICE_TOKEN=<mesmo-segredo-ou-token-de-servico>
SARA_REQUEST_TIMEOUT=30s

Reinicie o N07.

A descoberta deve listar as cinco operações sara.*. O N07 não cria uma nova identidade N08; ele registra e roteia o serviço regenerativo.

## 4. N04 e N06

Somente no ambiente server-side:

SARA_ENABLE_CHAT=true
SARA_BASE_URL=http://<host-sara>:8090
SARA_API_TOKEN=<token>

Depois de reiniciar o frontend, cada mensagem textual passa pelo ciclo SARA antes da geração do modelo, e o resultado é incorporado ao contexto regenerativo.

## 5. Segurança

Nunca commitar tokens.
N07 utiliza SARA_SERVICE_TOKEN somente no backend.
N04/N06 usam SARA_API_TOKEN somente no backend.
O Mesh continua usando SOUL_MESH_HMAC_SECRET e contractVersion 1.1.0 próprios do SOUL.

## 6. Critério de ativação real

A integração só é considerada ATIVA depois que:
1. /health retorna ready=true;
2. /v1/capabilities retorna sara.*;
3. um ciclo real retorna cycle_id e execution_report;
4. /v1/trace/{cycle_id} retorna integridade válida;
5. N07 executa sara.cycle via sua própria superfície;
6. N04 e N06 completam uma conversa real com SARA_ENABLE_CHAT=true;
7. os logs/resultados preservam correlation/cycle/trace;
8. todos os gates de testes e reauditoria passam.

Sem esses eventos observáveis, o estado permanece PROJETADO/BLOQUEADO, nunca "ativo por configuração".

## 4b. N01, N02, N03 e N05

N01 (branch canonica consolidacao-n01), N02 e N03 expõem as mesmas capacidades sara.* no respectivo gateway Mesh e chamam o serviço SARA por HTTP server-side.

N01/N02/N03 usam SARA_SERVICE_URL e SARA_SERVICE_TOKEN. N05 usa SARA_BASE_URL, SARA_API_TOKEN e SARA_ENABLE_CHAT=true para adicionar evidência regenerativa ao contexto conversacional.

Cada integração deve comprovar uma resposta real com cycle_id/correlation_id e estado de erro explícito quando SARA não estiver configurado.

## 8. Backends de ativação local

SARA_SANDBOX_DOCKER_IMAGE pode apontar para uma imagem Python já presente no host. Quando Docker e a imagem estão disponíveis, o bootstrap injeta DockerIsolationBackend real no SafeSandbox.

O QuantumCrawler inicializa backends HTTP reais para GitHub e HuggingFace. Tokens GITHUB_TOKEN e HF_TOKEN são opcionais para endpoints públicos e nunca são armazenados no código.

A detecção é fail-closed: não há promoção para capacidade ativa sem backend detectado.
