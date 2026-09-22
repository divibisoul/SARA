# SOUL + SARA — Auditoria Forense Global e Plano Unificado
Data: 2026-09-22
Escopo: SARA + N01–N07

## Regra de evidência
Existência de código, documentação ou configuração não equivale a execução. Estados: REAL, PROJETADO, BLOQUEADO, INCOMPLETO, INVÁLIDO, DUPLICADO, NÃO MEDIDO.
Falha: erro → evidência → classificação → contenção → causa-raiz → correção → teste → métrica → alerta → runbook → reauditoria.

## Estado executivo
SARA: auditoria/regeneração/ética/memória/rollback/governança. Estruturalmente avançado; E2E federado ainda precisa prova.
N01: coordenação Mesh, discovery, routing, Android/híbrido. SARA foi conectado na branch consolidacao-n01. Certificação ainda bloqueada pela execução do GitHub Actions.
N02: IA/provider/agents + Mesh. SARA conectado nesta continuação. E2E não medido.
N03: áudio/fala + Mesh. SARA conectado nesta continuação. E2E não medido.
N04: chat/tools/documentos/contexto/streaming + Mesh. SARA já conectado. E2E não medido.
N05: inferência/conversação + Mesh. SARA conectado nesta continuação. E2E não medido.
N06: cognição/support/pilot + Mesh. SARA já conectado. E2E não medido.
N07: orquestração/federação/compute/storage + Mesh. SARA já integrado. E2E não medido.

## Autoridade
SARA não é N08. SARA é autoridade regenerativa: auditoria, ética, estratégia/regeneração, memória, proveniência, rollback, evidência e governança interna.
N01 é autoridade de coordenação Mesh. N07 é autoridade de descoberta, roteamento e execução federada. N02–N06 preservam suas capacidades nativas.
Duplicações não são apagadas: são classificadas como autoridade, adapter de compatibilidade ou legado preservado.

## SARA — lacunas
SafeSandbox: execução isolada depende de backend real; ativação automática para Docker foi adicionada quando Docker + imagem existem.
QuantumCrawler: backends HTTP reais GitHub e HuggingFace foram adicionados ao bootstrap.
QuantumScanner: análise Python local existe; binário profundo exige toolchain/alvo.
LegalAI: validação de licença local existe; patente exige oracle externo.
DecisionTrace: cadeia local existe; publicação IPFS exige endpoint RPC.
TransystemSARA: assimilação externa exige credenciais e contratos.
GovernanceBackend: backend local existe; UI externa ainda é infraestrutura.
Nenhum desses estados pode ser mascarado por mock.

## Correções aplicadas
Novo activation.py com DockerIsolationBackend e backends HTTP reais.
Bootstrap passa a autoativar backends reais detectáveis e somente promove status quando a condição de execução existe.
QuantumCrawler teve encoding de query corrigido e verify_source deixou de ser um NotImplemented genérico.
Foi adicionado forensic_self_check.py e workflow sara-validation.yml.
N05 recebeu cliente server-side SARA e contexto regenerativo aditivo.
N01, N02 e N03 receberam integração direta com sara.*; N01 ficou restrito à branch canônica consolidacao-n01.

## Contrato SARA federado
sara.cycle → /v1/cycle
sara.audit → /v1/audit
sara.regenerate → /v1/regenerate
sara.state → /v1/state
sara.capabilities → /v1/capabilities
Correlation ID é preservado e autenticação é Bearer server-side. Falta de configuração gera erro explícito.

## Plano unificado
F1: fechar SARA standalone com execução real + testes + reauditoria.
F2: reconciliar autoridade do contrato soul-mesh/1 versão 1.1.0 sem apagar adapters.
F3: comprovar SARA em N01–N07 com pelo menos uma transação real.
F4: executar as 42 transações direcionais Mesh com capability nativa, correlação, resposta e evidência.
F5: transformar cada falha em teste permanente, métrica, alerta e playbook.
F6: ativar infraestrutura externa individualmente conforme backend real esteja disponível.
F7: somente depois promover estado ONLINE.

## Regra final
Nenhuma frente cancela outra. N01/ERU/Regra de Ouro continuam simultaneamente com SARA e a integração global. Nenhum componente existente é excluído.