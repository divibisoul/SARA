# SARA — Matriz de Lógica do Inventário

Esta matriz cobre o inventário funcional histórico e as camadas técnicas que o suportam.
Extensões de integração não são novos núcleos SOUL.

| Componente | Responsabilidade final | Lógica/execução | Fases | Estado |
|---|---|---|---|---|
| ARA | auditar e regenerar | detecta tags, complexidade e conflitos; plano não destrutivo; integridade | AUDIT, REGENERATION | REAL |
| ARA_Extended | aprofundar ARA | análise estrutural, relacional e semântica; preservação de relações; meta-auditoria | AUDIT, REGENERATION | REAL |
| ETR | validação ética | camadas lexical, contextual, identidade, strict e filtros culturais | ETHICS, VALIDATION | REAL |
| ETR_Extended | validação multicritério | quatro frameworks + frame semântico + validação de transformação + dissent | ETHICS, VALIDATION | REAL |
| ITR | estratégia/execução | análise de objetivo, variantes, registry de passos e execução | STRATEGY, EXECUTION | REAL LOCAL |
| ITR_Extended | planejamento composto | plano multi-fase, perfil semântico, rollback por fase e guard semântico | STRATEGY, EXECUTION | REAL LOCAL |
| TrinitySynergy | acoplamento ARA↔ETR↔ITR | detecta → planeja → valida → regenera → executa → converge | AUDIT–VALIDATION | REAL |
| SistemaVivo | fachada operacional | valida conexão, inicia ciclo, monitora e agrega evidência | 12 fases | REAL |
| RegenerativeLoop | ciclo nuclear | preflight, 12 fases, convergência, rollback, rastreabilidade | 12 fases | REAL |
| SynergyEngine | pipeline explícito | registra estágios e executa composição real | REGENERATION | REAL |
| RegenerativeState | estado do ciclo | máquina de estados com transições auditáveis | transversal | REAL |
| DNA_Tags | proteção ontológica | varredura, bloqueio e registro de violações | INGESTION | REAL |
| TemporalVectorDB | memória temporal/vetorial | persistência, consulta temporal/vetorial e integridade por registro | PERSISTENCE | REAL |
| RegenerativeMemory | memória versionada | snapshots versionados, diff e persistência | PERSISTENCE | REAL |
| ProvenanceTracker | origem das regras | cadeia de proveniência verificável | PERSISTENCE | REAL |
| IdentityCore | fronteiras de identidade | validação de regras identitárias e participação | IDENTITY | REAL |
| EmergencyRollback | reversão de estado | captura imutável, restauração e cadeia verificável | SNAPSHOT | REAL |
| EthicalFilterChain | composição ética | múltiplos filtros e gate | VALIDATION | REAL |
| SafeSandbox | isolamento | análise estática local; DockerIsolationBackend real quando Docker + imagem existem | EXECUTION | PARCIAL / BACKEND EXTERNO CONDICIONAL |
| StormMonitor | observabilidade operacional | sessões, amostragem de carga e anomalias | MONITORING | REAL LOCAL |
| DecisionTrace | trilha de decisões | cadeia hash thread-safe; IPFS separado | PERSISTENCE, MONITORING | REAL LOCAL / IPFS BLOQUEADO |
| GovernanceBackend | governança operacional | decisões, snapshots, overrides + UI HTML administrativa local autenticada | MONITORING, GOVERNANCE | REAL LOCAL |
| QuantumCrawler | descoberta tecnológica | backends HTTP reais GitHub/HuggingFace + coleta e verificação de origem; depende de rede no runtime | GOVERNANCE | IMPLEMENTADO COM ATIVAÇÃO HTTP |
| NeuralLens | análise de código | AST Python local + cliente GitHub remoto com ref opcional e Git blob SHA para proveniência de conteúdo | GOVERNANCE | REAL LOCAL |
| InnovationRadar | análise de candidatos | relevância, inovação, ética, estratégia e risco | GOVERNANCE | REAL |
| NeuroIntegrator | integração de candidatos | snapshot, persistência, validação e rollback transacional | SNAPSHOT, PERSISTENCE | REAL |
| QuantumScanner | inspeção profunda | scanner depende de acesso ao alvo/toolchain | — | BLOQUEADO POR INFRA |
| UbuntuEthics | filtro comunitário | avaliação de princípios e evidências lexicais | VALIDATION | REAL LOCAL |
| BuenVivir | filtro de harmonia | avaliação de princípios e evidências lexicais | VALIDATION | REAL LOCAL |
| LegalAI | conformidade jurídica | cadeia local de licenças; consulta de patentes externa | GOVERNANCE | REAL LOCAL / PATENTES BLOQUEADAS |
| LegalCompliance | regras de licença | registry de termos e validação de licenças | GOVERNANCE | REAL |
| GovernedSARA | decisão de governança | comitê + compliance + radar | GOVERNANCE | REAL |
| ARAForge | adaptação de manifestos | aplica restrições preservando prompt original | GOVERNANCE | REAL |
| AssimilationReviewCommittee | quórum de assimilação | avaliadores independentes e cálculo de quórum | GOVERNANCE | REAL |
| QuantumSnapshotSystem | snapshot meta | cópia de estado + ID + restauração | SNAPSHOT | REAL LOCAL |
| ERU_Engine | reversibilidade | freeze/diff estrutural + snapshots de capacidades, assinaturas e origem de métodos + evidência comportamental observada por probes; candidatos de recuperação sem reintegração automática | PERSISTENCE | REAL LOCAL |
| TransystemSARA | assimilação externa | interface para sistemas externos e credenciais | — | BLOQUEADO POR INFRA |
| CycleAuditor | auditoria do ciclo | verifica fases, abortos, persistência e snapshot | AUDIT, VALIDATION, MONITORING | REAL |

## Contratos técnicos

SaraModule define identidade, versão, status, papel, dependências e fases.
CyclePhase fixa as 12 fases.
CycleContext transporta estado corrente, artefatos, flags e evidência.
ModuleRegistry registra, resolve dependências e produz ordem topológica.
InvariantValidator bloqueia execução quando os contratos falham.

## Camada de integração

ConnectedRuntime é um componente de composição, não um novo núcleo SOUL. Ele conecta os módulos já existentes às fases sem duplicar as operações do RegenerativeLoop.

## Serviço

O serviço HTTP expõe o runtime real. A autenticação é Bearer para /v1/*; /health é público.
Operações versionadas:
- sara.cycle@1.0.0
- sara.audit@1.0.0
- sara.regenerate@1.0.0
- sara.state@1.0.0
- sara.trace@1.0.0
- sara.health@1.0.0

## Regra de maturidade

IMPLEMENTED só pode ser usado quando a lógica local correspondente existe.
Capacidades externas não são promovidas a IMPLEMENTED sem backend real, credencial, execução verificável e reauditoria.
## Conexão SOUL ↔ SARA — contrato federado

A conexão com o SOUL é aditiva: SARA continua autoridade de ARA/ETR/ITR, ERU, memória, proveniência, rastreabilidade e governança; os núcleos SOUL continuam proprietários de suas capacidades nativas. A afinidade abaixo define onde as funções se complementam, não transferência de propriedade.

| Núcleo | Funções SOUL relacionadas | Operações SARA com maior afinidade | Complemento SARA |
|---|---|---|---|
| N01 | gateway, Android, runtime/host, observabilidade | sara.health, sara.capabilities, sara.state, sara.trace, sara.cycle | ConnectedRuntime, DecisionTrace, GovernanceBackend |
| N02 | conversação, interação, cognição | sara.audit, sara.cycle, sara.regenerate, sara.trace | ARA_Extended, ETR_Extended, ITR_Extended |
| N03 | percepção, voz, multimodalidade | sara.audit, sara.regenerate, sara.trace | ARA_Extended, ETR_Extended, SafeSandbox |
| N04 | ferramentas, documentos, artefatos | sara.audit, sara.regenerate, sara.cycle, sara.trace | ARA_Extended, ETR_Extended, LegalAI, ProvenanceTracker |
| N05 | orquestração, despacho, execução | sara.cycle, sara.audit, sara.regenerate, sara.trace | TrinityERUUnified, ConnectedRuntime, CycleAuditor |
| N06 | cognição, síntese, auditoria, governança | sara.audit, sara.state, sara.trace, sara.regenerate, sara.cycle | ERU_Engine, GovernedSARA, DecisionTrace, ProvenanceTracker |

**Prova de conexão:** manifesto = contrato; configuração = URL + credencial; conexão = requisição HTTP real + resposta válida + correlação; falha = erro explícito. Declaração de afinidade não conta como execução.
