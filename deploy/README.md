# SARA — deployment architecture

## Current production boundary

The canonical runtime is a modular monolith: one Python process owns the regenerative state machine, registry, memory, security, governance and observability. This is the deployment topology required for the core to operate.

Startup sequence:
1. import packages;
2. construct every registered module;
3. register every module and collect failures;
4. resolve registry dependencies;
5. validate metadata and canonical phases;
6. fail closed if a blocking invariant is violated;
7. expose SistemaVivo.process as the execution boundary;
8. execute the 12 canonical phases;
9. persist temporal evidence, decision hashes, provenance and rollback snapshots;
10. emit a deterministic execution report.

PENDING_INFRASTRUCTURE modules are registered and visible but are never silently executed.

## Bounded contexts for future microservices

| Service | Bounded context | Main modules |
|---|---|---|
| sara-core | ARA/ETR/ITR + contracts | core, contracts |
| sara-regeneration | cycle state and regeneration | regeneration |
| sara-memory | temporal/vector + regenerative memory | memory |
| sara-security | identity, filters, rollback, sandbox | security |
| sara-governance | ethics, legal, governed admission | governance |
| sara-research | radar, lenses, crawlers, scanners | research |
| sara-meta | ERU, snapshots, assimilation | meta |
| sara-observability | DecisionTrace, reports, monitoring | monitoring, audit |

The microservice split is not a second implementation of the algorithms. Each service owns one bounded context and exposes the same versioned contracts currently used in-process.

## Communication contract

- synchronous request/response for a single regenerative cycle;
- immutable event records for phase evidence;
- correlation key = cycle_id;
- idempotency key = cycle_id + iteration;
- every cross-service mutation carries provenance and expected state hash;
- a service rejects a state transition when the previous hash does not match;
- timeouts and transport failures abort the affected phase and invoke rollback;
- no service acknowledges a mutation before durable evidence is written.

Recommended transport progression:
in-process calls -> HTTP/gRPC -> event broker

Do not introduce a broker before the monolith has stable contracts and deterministic tests.

## Distributed regeneration

A distributed cycle keeps one authoritative state hash. Each service receives:
cycle_id, phase, state_hash, payload, provenance_ref

and returns:
cycle_id, phase, previous_hash, new_state_hash, result, evidence_ref

The coordinator accepts a phase only when previous_hash equals the coordinator current hash. A mismatch is a hard failure and causes compensating rollback.

## Deployment progression

Stage A — local: python -m pytest
Stage B — container: build the Python package into one image and run the modular monolith.
Stage C — orchestrated monolith: run one SARA deployment with persistent storage for TemporalVectorDB, RegenerativeMemory and DecisionTrace.
Stage D — microservices: extract bounded contexts one at a time, keeping sara-core as contract authority. Start with observability/memory, then security/governance, then research/meta. The regeneration coordinator remains one authoritative state machine until distributed invariants are proven.

## External infrastructure gates

The following remain honestly pending because their real external backends are absent:
- SafeSandbox execution: Docker/Firecracker/nsjail backend;
- QuantumCrawler: real network APIs, credentials and rate limiting;
- QuantumScanner: real target/toolchain access;
- LegalAI patent checks: INPI/USPTO/EPO or equivalent oracle;
- DecisionTrace IPFS publication;
- TransystemSARA external-system credentials/contracts;
- GovernanceBackend UI/HTTP frontend.

These are not simulated. Their interfaces remain explicit and raise NotImplementedError until the required infrastructure is injected.
