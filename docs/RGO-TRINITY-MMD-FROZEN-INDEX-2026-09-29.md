# RGO Trinity MMD — Frozen Integration Index
Data: 2026-09-29

## Stage chain
RGO → ARA → ITR → ETR → ARA(re-generation) → ETR(validation) → ITR(execution) → ETR(validation) → ERU(snapshot) → MMD(scale)

## Inheritance
Each stage references the previous stage by output hash. The chain is data inheritance, not class inheritance.

## Channels
VagusNerveBus carries stage observations.
N01 HortaCore is the durable-in-runtime memory projection target through the existing N07 Mesh peer transport.

## Authority
RGO preserves finding/evidence.
ARA diagnoses/regenerates.
ITR plans/executes.
ETR validates.
ERU freezes historical state.
MMD records the explicit scale lens.

No stage deletes the state of another stage.
