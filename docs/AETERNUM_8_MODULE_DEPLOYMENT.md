# AETERNUM — 8 módulos sobre SOUL/SARA

Este documento registra a implantação não destrutiva dos oito domínios sobre a arquitetura já existente.

## Distribuição

1. M1 Core — N01.
2. M2 Orquestração — N01.
3. M3 Linguagem — N05 via SOUL Mesh.
4. M4 Mind — N06 via adaptador com binding externo.
5. M5 Percepção — N03 via adaptador.
6. M6 Imunidade — autoridades SARA: IdentityCore, EmergencyRollback, EthicalFilterChain e validação de invariantes.
7. M7 Evolução — ARAForge, RegenerativeLoop, InnovationRadar e proveniência.
8. M8 Governança/Memória — RegenerativeMemory, TemporalVectorDB, DecisionTrace, GovernanceBackend e proveniência.

## Regra de autoridade

O AETERNUM overlay não cria um segundo SARA, segundo ERU, segundo EventBus, segunda memória ou segundo transporte. Os componentes existentes continuam proprietários de suas capacidades.

## Prova e estados

- Estados externos são declarados como contrato federado/adaptador até existir uma conexão real.
- ASASF registra cada etapa e atribui a confirmação ao executor injetado; isso não equivale a verificação independente.
- O enforcement só declara completed quando existe executor real e um verifier explícito retorna sucesso. Sem verifier, o resultado é executed_unverified.
- Infraestrutura pendente nunca é convertida em sucesso sintético.

## Preservação

Esta camada é aditiva. Arquivos e autoridades existentes permanecem no lugar; correções devem ser aplicadas por adaptação, binding, validação e leitura retroativa, sem exclusão do legado.
