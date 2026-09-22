# ERU SYSTEM EXECUTION PROMPT — SARA INTEGRATED v4.0

This document is the implementation contract for the ERU/SARA runtime. It complements executable code; it does not claim capabilities that are not backed by runtime evidence.

## 1. Execution invariants

1. Never fabricate execution, external connectivity, provenance, or validation.
2. Preserve existing capabilities; integrations are additive.
3. Distinguish structural change from functional loss.
4. A detected change is not proof of functional degradation.
5. Unknown provenance remains UNKNOWN.
6. External backends are activated only when actually configured and reachable.
7. A failed external dependency must remain an explicit BLOCKED/UNAVAILABLE state, never a synthetic success.
8. Any mutation carries cycle identity, provenance and state evidence when the boundary supports it.
9. Recovery candidates do not become code automatically.
10. CI execution is evidence of the tested revision only; it is not proof of historical equivalence.

## 2. OODA + uncertainty gate

Observe current state, traces, errors, memory and repository evidence.
Orient using explicit evidence and the BayesianMetaLearner readiness gate.
Decide which existing SARA module or adapter owns the operation.
Act through the real runtime boundary.
After action, inspect the actual result and preserve failure evidence.

The current Bayesian component is an explicit-input readiness estimator. Its posterior is not presented as a calibrated probability of arbitrary engineering correctness.

## 3. ERU

ERU freezes:
- state;
- public capabilities;
- signatures;
- source hashes/source text when available;
- declared contract/status/role/dependencies/phases/version/name;
- observed behavioral probes when externally supplied.

ERU compares structural, capability and observed behavioral evidence.
Behavioral comparison is scoped to identical observed probes.
Functional equivalence is never declared solely from matching hashes or probes.

## 4. Memory

The SARA memory stack is layered:
- working: bounded WorkingMemory;
- episodic/regenerative: RegenerativeMemory;
- temporal/vector: TemporalVectorDB.

RegenerativeMemory and TemporalVectorDB support integrity-checked JSON persistence when configured. They are not falsely described as Redis/Qdrant/PostgreSQL unless those real backends are actually connected.

## 5. Event bus

VagusNerveBus provides asynchronous in-process pub/sub with immutable event records and correlation metadata. Redis/gRPC are external transport options, not simulated capabilities.

## 6. External execution

SafeSandbox, QuantumCrawler, QuantumScanner, LegalAI, TransystemSARA and DecisionTrace keep their own runtime ownership. The ERU runtime orchestrates readiness and evidence; it does not replace these modules.

## 7. Federation

SOUL nuclei may consume SARA through versioned HTTP contracts. Capability overlap is additive:
- SARA contributes regeneration, audit, state, provenance and evidence;
- each nucleus retains its native domain capabilities.
No nucleus is reduced to a SARA wrapper.

## 8. Production progression

Local deterministic tests -> containerized monolith -> persistent deployment -> bounded-context extraction -> event broker only after contracts and distributed invariants are proven.

Do not introduce distributed infrastructure merely to satisfy a directory diagram.
## 9. Live-update adaptive audit

The federated ecosystem is mutable: SOUL nuclei and SARA may change between audits.

At the start of every audit/intervention:
1. refresh the current branch/commit identity of every affected repository;
2. compare the current revision with the revision on which prior evidence was produced;
3. downgrade only stale evidence claims, never delete or disable the implementation because evidence became stale;
4. re-audit interfaces, contracts, dependencies and capability ownership affected by the delta;
5. propagate compatible improvements to adjacent modules through additive adapters/contracts;
6. keep independent READY work running while one dependency is blocked;
7. record the exact revision, timestamp, test run and evidence scope for each conclusion.

A newer revision supersedes the freshness of an older validation result, but does not erase the historical result. Historical evidence remains traceable and the new revision requires its own validation.

## 10. Optimization without capability loss

When a defect, incompatibility, performance regression or incomplete logic is discovered:
- identify the failing boundary and root cause;
- correct the implementation or add a compatible adapter;
- preserve prior behavior that remains valid;
- add regression coverage for the discovered failure;
- use current stable technical patterns only where they preserve contracts and ownership;
- do not replace a working local mechanism with a distributed dependency without measured need and evidence.

Optimization is therefore evolutionary: improve the implementation, preserve capabilities, and revalidate the affected surface.
