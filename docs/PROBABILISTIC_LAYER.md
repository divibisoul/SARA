# SARA ProbabilisticReasoningLayer v1

## Purpose

The layer adds measurable uncertainty and dependency context to the existing SARA
cycle. It does **not** replace ARA, ETR, ITR, regeneration, rollback, or Omega.

## Activation

`PROBABILISTIC_LAYER=true` enables the adapter. The default is disabled, preserving
the legacy cycle path when no probabilistic context is requested.

## Bayesian update

For a node with prior distribution p, prior concentration c, Laplace pseudo-count λ,
and observed evidence e:

`count_i = p_i * c + λ + e_i`

`posterior_i = count_i / Σ count_j`

Defaults: `c=1.0`, `λ=1.0`.

Without evidence, the posterior equals the supplied prior. Evidence may be one-hot or
soft counts.

## Neural probability

A deterministic CPU-first encoder accepts either explicit logits or an explicit
linear map `logits = W x + b`. Calibration uses:

`softmax_i(z,T) = exp(z_i/T) / Σ exp(z_j/T)`

The layer records entropy and maximum probability. No online weight training is
performed in the SARA cycle.

## Fusion

When both evidence and neural logits exist:

`p_fused(i) ∝ p_dirichlet(i)^α * p_neural(i)^β`

with defaults `α=0.5`, `β=0.5`, followed by normalization.

The result reports `source=dirichlet|neural|fused` plus node provenance.

## Causal structure and interventions

The layer validates a discrete DAG and `do()`/evidence node-state references.
It intentionally does not claim causal effect inference without conditional
probability tables. Full pgmpy-style causal inference remains an optional
`PENDING_INFRASTRUCTURE` adapter.

## Failure behavior

Invalid states, priors, graph edges, neural dimensions, temperatures, evidence, or
interventions produce deterministic validation errors when the feature is enabled.
When the feature is disabled, the SARA cycle remains on its pre-existing path.

## Observability

Probabilistic output is copied into cycle artifacts and DecisionTrace. Confidence,
entropy, posterior and provenance are exposed as auxiliary evidence only.
