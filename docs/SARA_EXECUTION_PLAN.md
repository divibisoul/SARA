# SARA — Plano de Execução do Início ao Fim

## Etapa 0 — integridade estrutural
Dependências: nenhuma.
Implementar/validar contratos, registry, ordem topológica, invariantes, provenance e estados.
Gate: bootstrap fail-closed; grafo acíclico; 12 fases válidas.

## Etapa 1 — núcleo regenerativo
Dependências: Etapa 0.
ARA + ARA_Extended, ETR + ETR_Extended, ITR + ITR_Extended, TrinitySynergy e RegenerativeLoop.
Gate: detecção lexical/semântica/estrutural/relacional, validação ética, estratégia, execução transacional e convergência.

## Etapa 2 — memória, segurança e reversibilidade
Dependências: Etapa 1.
DNA_Tags, IdentityCore, TemporalVectorDB, RegenerativeMemory, DecisionTrace, ProvenanceTracker, EmergencyRollback, ERU e snapshots.
Gate: cada ciclo produz estado, evidência, trace, persistência e ponto restaurável.

## Etapa 3 — integração interna
Dependências: Etapas 1–2.
ConnectedRuntime integra módulos não-nucleares por fase sem duplicar ARA/ETR/ITR.
Gate: falha de operação IMPLEMENTED é bloqueante; PENDING_INFRASTRUCTURE permanece explicitamente pendente.

## Etapa 4 — serviço SARA
Dependências: Etapas 0–3.
Ativar serviço HTTP, autenticação Bearer, limites de request, capabilities e trace.
Gate: /health, /v1/capabilities, /v1/cycle, /v1/audit, /v1/regenerate, /v1/state e /v1/trace/{cycle_id} respondem conforme contrato.

## Etapa 5 — N07
Dependências: Etapa 4.
Configurar SARA_SERVICE_URL/SARA_SERVICE_TOKEN; registrar sara.* no Engine; preservar correlation/trace; transportar payload estruturado no Mesh.
Gate: N07 descobre e executa sara.* por execute e intent; resultados retornam com correlationId e metadata de evidência.

## Etapa 6 — N04
Dependências: Etapa 4.
Ativar SARA_ENABLE_CHAT, SARA_BASE_URL e SARA_API_TOKEN no backend; ciclo SARA antes do streamText.
Gate: conversa real preserva UX, tools, documentos e streaming e recebe contexto regenerativo com cycle/trace/evidence.

## Etapa 7 — N06
Dependências: Etapa 4.
Mesmo contrato, preservando cognição, auditoria, governança e streaming próprio do N06.
Gate: conversa real com SARA habilitado mantém rastreabilidade e não duplica ARA/ETR/ITR.

## Etapa 8 — infraestrutura externa
Dependências: módulos e credenciais específicas.
SafeSandbox isolado, QuantumCrawler, QuantumScanner, IPFS, oracle jurídico, TransystemSARA e UI de governança.
Gate individual: backend real + credencial real + teste real + reauditoria. Nenhum mock é permitido.

## Etapa 9 — persistência federada/produção
Dependências: Etapas 4–8.
Conectar Supabase/observabilidade/persistência externa quando o contrato e as credenciais estiverem disponíveis.
Gate: recuperação de estado e evidência após restart/redeploy, sem quebra de integridade.

## Etapa 10 — extração de microserviços
Dependências: monólito modular comprovado em produção.
Extrair bounded contexts somente quando carga, isolamento, disponibilidade ou ciclo de vida justificarem.
Gate: contratos externos permanecem compatíveis; a lógica do núcleo não é duplicada.

## Definition of Done — SARA standalone
- bootstrap pronto e fail-closed;
- 12 fases executam em ordem;
- ARA/ETR/ITR e Trindade produzem resultados verificáveis;
- memória, provenance, trace e rollback íntegros;
- serviço HTTP autenticado disponível;
- nenhum módulo externo é tratado como ativo sem infraestrutura.

## Definition of Done — SARA federado
- N07 registra e executa sara.*;
- Mesh mantém HMAC/correlation/anti-replay do contrato existente;
- N04 e N06 consomem SARA server-side;
- cycle_id, trace_id, correlation_id, evidence_hash e estado final podem ser relacionados;
- falhas propagam status real;
- CI e E2E de cada repositório passam no ambiente de execução real.

## Regra de fechamento
Uma etapa não é considerada concluída por existência de código ou documentação. O gate exige implementação, execução real, teste, validação, reauditoria e evidência. Na ausência de execução comprovada, o estado permanece UNMEASURABLE.