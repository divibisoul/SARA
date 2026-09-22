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

## Atualização forense — ciclo de correção 2

### Falhas reais encontradas e corrigidas
- N03 possuía duas autoridades efetivas do protocolo Mesh: `src/mesh/SoulMeshProtocol.ts` e `lib/soul-mesh/SoulMeshProtocol.ts`. A primeira foi convertida em facade de compatibilidade, preservando APIs `createMessage`/ `validateMessage` sem manter uma segunda autoridade.
- N06 tinha dependência de runtime ausente: `lib/db/migrate.ts` importava `dotenv`, mas `package.json` não a declarava. `dotenv` foi recolocado no package manifest e lockfile. Antes da correção, o Build falhava com `MODULE_NOT_FOUND: dotenv`.
- N06 diagnostics tinha ordem incorreta: `setup-node` tentava inicializar cache pnpm antes de instalar pnpm. O workflow foi reordenado para pnpm/action-setup → setup-node. Após a correção, a rotina ultrapassou a falha de toolchain e alcançou o Build.
- N07 `supergpu/runtime.go` continha erro sintático real no envio de job do `BatchParallel`; a correção restaura o `case jobs <- job{...}:` válido.
- N07 auditoria arquitetural estava bloqueada pelo uso obrigatório de uma credencial cross-repository não disponível. O workflow agora usa o token interno quando possível e não transforma falta de prova remota em falha estrutural do código; a ausência de proveniência remota continua registrada como degradação.
- N07 matrix teve os `sourceRef` reconciliados com os HEADs reais registrados para N01–N06.
- N07 live-source audit foi ajustado para distinguir `FAIL` estrutural de `DEGRADED` por ausência de acesso remoto.
- N07 normalize-main deixou de atingir o primeiro erro sintático conhecido; novas execuções serão o gate para confirmação.
- N01 continua com a mesma falha pré-step do Actions; o rerun não produziu steps nem logs. Isso permanece infraestrutura não atribuída ao código.

### Prova positiva já obtida
- SARA validation run 62 e SARA CI run 324 concluíram com sucesso no commit b1add77.
- N06 Channel Contract e Soul Mesh CI concluíram com sucesso no commit f5ae996.
- Antes da correção de dotenv, N06 diagnostics conseguiu executar setup/checkout/instalação, evidenciando ambiente real e permitindo identificar a dependência ausente.

### Estado atualizado
SARA = VALIDADO no último commit com execução verde registrada; mudanças posteriores àquele commit exigem nova execução para reconfirmação.
N04 = mantém execução verde previamente observada.
N06 = Mesh/Channel Contract verdes após correções; diagnostics e build estão em nova rodada após correção de dotenv.
N07 = correções estruturais aplicadas; nova CI em execução/aguardando prova.
N01/N02/N03/N05 = ainda sem evidência executável suficiente nas respectivas rodadas principais; falhas atuais são predominantemente pré-step e devem permanecer separadas de defeitos de código até logs executáveis aparecerem.

### Regra
Cada novo erro encontrado nesta auditoria entra no ciclo de resiliência e gera correção/teste/documentação; nenhuma implementação existente é apagada.
