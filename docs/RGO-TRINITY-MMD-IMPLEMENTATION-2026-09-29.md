# RGO + ARA + ITR + ETR + ERU + MMD — Implementação

Estado: branch rgo-trinity-mmd-2026-09-28.

## Processador composto
RGOTrinityProcessor compõe os módulos existentes sem substituí-los.

Sequência efetiva:
RGO → ARA → ITR → ETR → ARA (regeneração) → ETR (validação) → ITR (execução) → ETR (validação final) → ERU (snapshot) → MMD (escala).

## Herança
A herança é de estado e evidência. Cada StageEnvelope recebe o output_hash da etapa anterior como parent_hash e input_hash e também recebe sequence_index crescente. Isso preserva a sequência sem destruir a independência semântica de cada núcleo.

## ERU
O ERUTrinityBridge existente continua sendo a ponte histórica. O processador registra snapshots de capacidade dos módulos ARA/ETR/ITR e observa cada etapa pela bridge; não é criada uma segunda autoridade de reversibilidade.

## RGO
Cada StageEnvelope é anexado ao ledger de evidência do RGO com uma cadeia hash separada, correlacionada ao finding original. Assim ARA, ITR, ETR, ERU e MMD deixam de ser apenas consumidores do finding e passam a produzir evidência vinculada à mesma genealogia.

## Vagus
Cada etapa é emitida no VagusNerveBus existente como RGO_TRINITY_STAGE e o ledger RGO também produz RGO_STAGE_EVIDENCE. O Vagus continua sendo barramento de eventos; não substitui o Soul Mesh.

## HortaCore
N01 continua dono do HortaCore. N07 encaminha cada StageEnvelope por Soul Mesh usando rgo.hortacore.store, incluindo output_hash, parent_hash, ERU snapshot e RGO evidence chain hash.

## MMD
MicroMacroManager é reutilizado da instância existente dentro do SoulETROmegaSystem. A pipeline usa transition_explicit para manter a escala observável e sem inventar política de parada.

## Integridade
Um teste deve demonstrar, para toda etapa, sequence_index crescente, parent_hash igual ao output_hash anterior, ERU snapshot existente, RGO evidence chain existente e integridade dos dois ledgers.