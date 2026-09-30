# FASE 0 — SARA TOOLS / CAPABILITIES

## B1 IDENTIDADE
Primário: regeneração, auditoria, governança, ética, proveniência e rollback.
Secundários: Trinity/ERU, Vagus, OctaCore, memória temporal, pesquisa e conexões.
Papel octacore: processador regenerativo/governança que amplia todos os núcleos sem absorver seu ownership.

## B2 PROCESSADORES
| Nome | Path | Estado |
|---|---|---|
| ARA / ARA_Extended | src/sara/core/ara*.py | ativo |
| ITR / ITR_Extended | src/sara/core/itr*.py | ativo |
| ETR / ETR_Extended | src/sara/core/etr*.py | ativo |
| TrinitySynergy | src/sara/core/trinity_synergy.py | ativo |
| TrinityERUUnified | src/sara/core/trinity_eru_unified.py | ativo |
| ERU_Engine | src/sara/meta/eru_engine.py | ativo |
| ERUTrinityBridge | src/sara/meta/eru_trinity_bridge.py | ativo |
| RegenerativeLoop | src/sara/regeneration/regenerative_loop.py | ativo |
| VagusNerveBus | src/sara/infra/vagus_bus.py | ativo |
| OctaCoreG0Kernel | src/sara/meta/octacore_kernel.py | ativo |
| OctaCoreMeshFusion | src/sara/meta/octacore_mesh_fusion.py | ativo |
| AeternumChimeraBridge | src/sara/meta/aeternum_chimera.py | ativo |
| RGOEngine | src/sara/rgo/engine.py | ativo; integração Trinity da #24 branch-only |

## B3 ENDPOINTS
| Método | Path | Estado |
|---|---|---|
| GET | /health | EXECUTABLE |
| GET | /v1/state | EXECUTABLE |
| GET | /v1/capabilities | EXECUTABLE |
| GET | /v1/trace/<cycle> | EXECUTABLE |
| POST | /v1/cycle | EXECUTABLE |
| POST | /v1/audit | EXECUTABLE |
| POST | /v1/regenerate | EXECUTABLE |
| POST | /v1/vagus | EXECUTABLE |
| POST | /v1/rgo/ingest | EXECUTABLE |
| POST | /v1/rgo/trinity | BRANCH_ONLY (#24) |

## B4 FUNÇÕES PRINCIPAIS
| Módulo | Função | Assinatura resumida | Consumidores |
|---|---|---|---|
| TrinityERUUnified | apply_to | (target) -> UnifiedERUReport | SARA/RGO |
| ERU_Engine | freeze/snapshot_state | (name,state) | bridge |
| Vagus | publish/publish_sync | (source,target,type,payload,...) | SARA/OctaCore |
| RGOEngine | ingest/record_stage_evidence | payload/stage metadata | RGO boundary |
| RegenerativeLoop | run/cycle | contexto | SistemaVivo |
| OctaCoreMeshFusion | process/operations | runtime envelope | Mesh federation |

## B5 EVENTOS
VagusNerveBus publica eventos com event_id, correlation_id, priority, ttl, source/target e payload. Consumidores incluem ConnectedRuntime, ciclo regenerativo e OctaCore fusion.

## B6 EVENTOS ESCUTADOS
Vagus subscribers são registrados por módulos; lista exaustiva não foi enumerada nesta sessão: PENDING.

## B7 EXTERNOS
Redis opcional; Docker/SafeSandbox opcional; embeddings; network crawlers; patent oracle; transystem adapters; SARA não usa esses componentes como presentes sem configuração.

## B8 INTER-NÚCLEO
N07 pode chamar SARA por HTTP; SARA expõe Vagus e Mesh fusion; N01/N02/N03/N04/N05/N06 podem entrar por boundaries federativas conforme contrato.

## B9 ADORMECIDAS
| Ferramenta | Precisa de | Estado |
|---|---|---|
| RGO Trinity/MMD | PR #24 + serviços reais | BRANCH_ONLY |
| external Redis | Redis config | BLOCKED_ENV |
| Docker sandbox | backend Docker | BLOCKED_ENV |
| network crawler | backend URLs/credentials | BLOCKED_ENV |
| patent oracle | config | BLOCKED_ENV |
| transystem adapters | adapter credentials | BLOCKED_ENV |

## B10 EXECUTÁVEIS
Bootstrap modular, TrinityERUUnified, Vagus in-process, OctaCore G0/Mesh fusion e Bayesian runtime parameters têm implementação real no MAIN. LIVE externo continua sujeito a ambiente.

## B11 EXPANSÃO
| Ao conectar com | Ganha | Perde | Neutro |
|---|---|---|---|
| N07 | orchestration | nenhum ownership | governance |
| N01 | runtime/Horta/Mesh | nenhuma | regeneration |
| N02 | conversation | nenhuma | governance |
| N03 | perception | nenhuma | ethics |
| N04 | tools/docs | nenhuma | governance |
| N05 | inference | nenhuma | strategy |
| N06 | context/session | nenhuma | provenance |
