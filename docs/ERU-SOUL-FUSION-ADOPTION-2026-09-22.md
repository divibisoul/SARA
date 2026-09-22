# ERU ↔ SOUL — Adoção do Material ERU e Auditoria Forense
Data: 2026-09-22

## Resultado da auditoria

SARA já contém a implementação mais madura da ERU no ecossistema:
- ERU_Engine v2;
- ERUDriftDetector;
- ERUTrinityBridge;
- ERURecoveryAdvisor;
- TrinityERUUnified;
- snapshots;
- provenance;
- ConnectedRuntime;
- integração no RegenerativeLoop.

Portanto, o material novo não deve gerar um segundo ERU.

## Novas capacidades que o material propõe

1. memória de trabalho/episódica/semântica;
2. event bus assíncrono;
3. avaliação explícita de incerteza;
4. adapters para execução;
5. contratos de infraestrutura;
6. telemetria;
7. integração com SOUL;
8. integração com SARA;
9. execução real em ambiente local/cloud.

## Auditoria crítica

### A — BayesianMetaLearner

O código apresentado calcula log-odds a partir de três números heurísticos. Isso pode ser usado como mecanismo de score, mas não como probabilidade Bayesiana calibrada sem dados de calibração.

Estado: PROPOSTO/HEURÍSTICO.

A implementação futura deverá separar:
- heuristic readiness score;
- calibrated probability;
- execution authorization.

### B — VagusNerveBus

O código é um event bus in-process. Não prova Redis, gRPC ou baixa latência distribuída.

Estado: IMPLEMENTAÇÃO LOCAL.

O SARA deverá manter seu contrato interno e utilizar transporte federado já existente para comunicação externa.

### C — ERUCoreController

O código fornecido retorna SUCCESS sem executar a tarefa.

Estado: NÃO EXECUTÁVEL COMO PROVA.

Não promover para produção sem um executor real e evidence recorder.

### D — Docker Compose

É infraestrutura declarativa. Não constitui runtime ativo sem build/startup/health evidence.

## Fusão com SARA

O novo material será acoplado aos pontos já existentes:

```
ERU Engine
↕
ERU Trinity Bridge
↕
Trinity/ARA/ETR/ITR
↕
RegenerativeLoop
↕
ConnectedRuntime
↕
SARA HTTP
↕
SOUL/N01 + N07
```

O ERU continua observacional/reconstrutivo onde o contrato atual assim determina. Qualquer promoção para mutação automática exige nova validação.

## Preservação

O material anterior permanece preservado como referência. Nenhuma implementação ERU existente será removida.

## Próximo gate

Auditar os contratos existentes contra:
- correlation;
- event version;
- snapshot identity;
- provenance;
- uncertainty semantics;
- execution evidence;
- recovery evidence;
- rollback evidence.

Depois implementar somente gaps comprovados.
