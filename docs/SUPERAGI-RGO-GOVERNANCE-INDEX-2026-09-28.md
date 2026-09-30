# SARA — Índice de Governança da Integração RGO / SUPER AGI
Data: 2026-09-28

SARA é a fronteira de governança, provenance, regeneração e reauditoria desta integração.

## Contrato canônico
F → N(F) → D(F) → C(D(F)) → I → V → H.

## Regra de preservação
Nenhum finding BugShield é apagado na adaptação. O payload original permanece em extensions.bugshield.

## Barramentos
VagusNerveBus permanece o barramento de eventos existente. Não foi criado um segundo Vagus.
Soul Mesh 1.1.0 permanece o transporte inter-núcleos.
HortaCore não é recriado em SARA.

## RGOEngine
A instância RGOEngine é criada no bootstrap e recebe a mesma instância de ProvenanceTracker e VagusNerveBus já usados pelo runtime.

Endpoints reais nesta branch:
- POST /v1/rgo/ingest
- GET /v1/rgo/state

## Segurança epistemológica
Finding sem correction_boundary não recebe dual inventado. O estado permanece UNRESOLVED.

## Estado de CI
O workflow rgo-integration da branch desta integração concluiu SUCCESS no último commit verificado.

## Relação com N07
N07 expõe rgo.ingest@1.0.0 e usa SARAProxy.RGOIngest para esta fronteira.
