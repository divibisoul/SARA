"""SARA — ProbabilisticReasoningLayer.

Pure-Python, low-dimensional Bayesian + calibrated neural uncertainty adapter.
It provides context/evidence only; SARA's ARA/ETR/ITR remain authoritative.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import os
from typing import Any, Mapping, Sequence


class ProbabilisticReasoningError(ValueError):
    """Deterministic validation error for probabilistic context."""


@dataclass(frozen=True)
class BayesianNode:
    name: str
    states: tuple[str, ...]
    prior: dict[str, float]
    prior_type: str = "uniform"
    pseudo_counts: float = 1.0
    evidence: dict[str, float] | None = None
    posterior: dict[str, float] | None = None
    confidence: float = 0.0
    entropy: float = 0.0
    provenance: str = "INFERRED"
    source: str = "dirichlet"


@dataclass(frozen=True)
class BayesianStructure:
    edges: tuple[tuple[str, str], ...]
    valid: bool
    validation_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class Intervention:
    name: str
    do: dict[str, str]
    evidence: dict[str, str]
    query: tuple[str, ...]


class ContinuousToDiscrete:
    """Stable scalar-to-label discretizer used only for Bayesian nodes."""

    def __init__(self, bins: Mapping[str, Sequence[float]] | None = None) -> None:
        self._bins = {
            str(name): tuple(float(value) for value in edges)
            for name, edges in (bins or {}).items()
        }
        for name, edges in self._bins.items():
            if any(not math.isfinite(v) for v in edges):
                raise ProbabilisticReasoningError(f"INVALID_BIN:{name}")
            if tuple(sorted(edges)) != edges:
                raise ProbabilisticReasoningError(f"UNSORTED_BINS:{name}")
            if len(set(edges)) != len(edges):
                raise ProbabilisticReasoningError(f"DUPLICATE_BINS:{name}")

    def transform(self, name: str, value: float, labels: Sequence[str] | None = None) -> str:
        key = str(name)
        if key not in self._bins:
            raise ProbabilisticReasoningError(f"BINS_NOT_CONFIGURED:{key}")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ProbabilisticReasoningError(f"NONFINITE_VALUE:{key}")
        edges = self._bins[key]
        label_values = tuple(labels) if labels is not None else tuple(
            [f"bin_{index}" for index in range(len(edges) + 1)]
        )
        if len(label_values) != len(edges) + 1:
            raise ProbabilisticReasoningError(f"LABEL_COUNT_MISMATCH:{key}")
        index = 0
        while index < len(edges) and numeric >= edges[index]:
            index += 1
        return str(label_values[index])


class NeuralProbEncoder:
    """Lightweight deterministic logits → calibrated probability encoder.

    No hidden/trained weights are invented. Vector inference requires explicit
    weights/bias supplied by the caller; otherwise logits can be provided directly.
    """

    @staticmethod
    def softmax(logits: Sequence[float], temperature: float = 1.0) -> list[float]:
        values = [float(v) for v in logits]
        if not values:
            raise ProbabilisticReasoningError("EMPTY_LOGITS")
        if any(not math.isfinite(v) for v in values):
            raise ProbabilisticReasoningError("NONFINITE_LOGITS")
        t = float(temperature)
        if not math.isfinite(t) or t <= 0:
            raise ProbabilisticReasoningError("INVALID_TEMPERATURE")
        scaled = [v / t for v in values]
        maximum = max(scaled)
        exps = [math.exp(v - maximum) for v in scaled]
        total = sum(exps)
        if not math.isfinite(total) or total <= 0:
            raise ProbabilisticReasoningError("SOFTMAX_NUMERICAL_FAILURE")
        return [value / total for value in exps]

    @staticmethod
    def entropy(probabilities: Sequence[float]) -> float:
        values = [float(v) for v in probabilities]
        return -sum(v * math.log(v) for v in values if v > 0)

    def encode_logits(self, logits: Sequence[float], temperature: float = 1.0) -> dict[str, Any]:
        probabilities = self.softmax(logits, temperature)
        return {
            "logits": [float(v) for v in logits],
            "probabilities": probabilities,
            "temperature": float(temperature),
            "entropy": self.entropy(probabilities),
            "max_probability": max(probabilities),
        }

    def encode(
        self,
        vector: Sequence[float],
        weights: Sequence[Sequence[float]],
        bias: Sequence[float] | None = None,
        temperature: float = 1.0,
    ) -> dict[str, Any]:
        x = [float(v) for v in vector]
        if not x or any(not math.isfinite(v) for v in x):
            raise ProbabilisticReasoningError("INVALID_NEURAL_VECTOR")
        matrix = [[float(v) for v in row] for row in weights]
        if not matrix or any(len(row) != len(x) for row in matrix):
            raise ProbabilisticReasoningError("INVALID_NEURAL_WEIGHTS")
        b = [0.0] * len(matrix) if bias is None else [float(v) for v in bias]
        if len(b) != len(matrix) or any(not math.isfinite(v) for v in b):
            raise ProbabilisticReasoningError("INVALID_NEURAL_BIAS")
        logits = [sum(weight * value for weight, value in zip(row, x)) + offset
                  for row, offset in zip(matrix, b)]
        return self.encode_logits(logits, temperature)


class ProbabilisticReasoningLayer:
    NAME = "ProbabilisticReasoningLayer"
    VERSION = "1.0"
    STATUS = "IMPLEMENTED"

    def __init__(
        self,
        *,
        enabled: bool | None = None,
        prior_strength: float = 1.0,
        alpha_dirichlet: float = 0.5,
        beta_neural: float = 0.5,
        temperature: float = 1.0,
    ) -> None:
        self.enabled = self._env_bool("PROBABILISTIC_LAYER", False) if enabled is None else bool(enabled)
        self.prior_strength = float(prior_strength)
        self.alpha_dirichlet = float(alpha_dirichlet)
        self.beta_neural = float(beta_neural)
        self.temperature = float(temperature)
        if not math.isfinite(self.prior_strength) or self.prior_strength <= 0:
            raise ProbabilisticReasoningError("INVALID_PRIOR_STRENGTH")
        if not math.isfinite(self.alpha_dirichlet) or self.alpha_dirichlet < 0:
            raise ProbabilisticReasoningError("INVALID_ALPHA")
        if not math.isfinite(self.beta_neural) or self.beta_neural < 0:
            raise ProbabilisticReasoningError("INVALID_BETA")
        if not math.isfinite(self.temperature) or self.temperature <= 0:
            raise ProbabilisticReasoningError("INVALID_TEMPERATURE")
        self.neural = NeuralProbEncoder()

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _normalize(values: Mapping[str, float]) -> dict[str, float]:
        numeric = {str(k): float(v) for k, v in values.items()}
        if not numeric or any(not math.isfinite(v) or v < 0 for v in numeric.values()):
            raise ProbabilisticReasoningError("INVALID_DISTRIBUTION")
        total = sum(numeric.values())
        if not math.isfinite(total) or total <= 0:
            raise ProbabilisticReasoningError("ZERO_DISTRIBUTION")
        return {key: value / total for key, value in numeric.items()}

    @staticmethod
    def _validate_node(raw: Mapping[str, Any]) -> tuple[tuple[str, ...], dict[str, float]]:
        states_raw = raw.get("states")
        if not isinstance(states_raw, list) or not states_raw:
            raise ProbabilisticReasoningError("STATES_REQUIRED")
        states = tuple(str(state) for state in states_raw)
        if len(set(states)) != len(states) or any(not state for state in states):
            raise ProbabilisticReasoningError("INVALID_STATES")
        prior_raw = raw.get("prior")
        if not isinstance(prior_raw, Mapping):
            raise ProbabilisticReasoningError("PRIOR_REQUIRED")
        prior = {str(state): float(prior_raw.get(state, 0.0)) for state in states}
        if any(key not in states for key in prior_raw):
            raise ProbabilisticReasoningError("PRIOR_STATE_UNKNOWN")
        total = sum(prior.values())
        if any(not math.isfinite(v) or v < 0 for v in prior.values()) or abs(total - 1.0) > 1e-6:
            raise ProbabilisticReasoningError("PRIOR_SUM_INVALID")
        return states, prior

    @staticmethod
    def _structure(raw_edges: Any, node_names: set[str]) -> BayesianStructure:
        errors: list[str] = []
        edges: list[tuple[str, str]] = []
        if raw_edges is None:
            return BayesianStructure((), True, ())
        if not isinstance(raw_edges, list):
            return BayesianStructure((), False, ("EDGES_MUST_BE_LIST",))
        for edge in raw_edges:
            if not isinstance(edge, list) or len(edge) != 2:
                errors.append("INVALID_EDGE")
                continue
            parent, child = str(edge[0]), str(edge[1])
            if parent not in node_names or child not in node_names:
                errors.append(f"EDGE_NODE_UNKNOWN:{parent}->{child}")
                continue
            if parent == child:
                errors.append(f"SELF_EDGE:{parent}")
            pair = (parent, child)
            if pair not in edges:
                edges.append(pair)
        if errors:
            return BayesianStructure(tuple(edges), False, tuple(errors))

        graph = {name: [] for name in node_names}
        for parent, child in edges:
            graph[parent].append(child)
        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(node: str) -> bool:
            if node in visiting:
                return False
            if node in visited:
                return True
            visiting.add(node)
            if any(not dfs(child) for child in graph[node]):
                return False
            visiting.remove(node)
            visited.add(node)
            return True

        if any(not dfs(name) for name in node_names):
            errors.append("CYCLE_DETECTED")
        return BayesianStructure(tuple(edges), not errors, tuple(errors))

    @staticmethod
    def _posterior_dirichlet(
        prior: Mapping[str, float],
        evidence: Mapping[str, float] | None,
        pseudo_counts: float,
        prior_strength: float,
    ) -> dict[str, float]:
        if pseudo_counts < 0 or not math.isfinite(pseudo_counts):
            raise ProbabilisticReasoningError("INVALID_PSEUDO_COUNTS")
        if evidence is None:
            return ProbabilisticReasoningLayer._normalize(prior)
        evidence_norm = {key: float(value) for key, value in evidence.items()}
        if any(key not in prior for key in evidence_norm):
            raise ProbabilisticReasoningError("EVIDENCE_STATE_UNKNOWN")
        if any(not math.isfinite(v) or v < 0 for v in evidence_norm.values()):
            raise ProbabilisticReasoningError("INVALID_EVIDENCE")
        counts = {
            state: float(prior[state]) * prior_strength + pseudo_counts + evidence_norm.get(state, 0.0)
            for state in prior
        }
        return ProbabilisticReasoningLayer._normalize(counts)

    def _node(self, raw: Mapping[str, Any]) -> BayesianNode:
        name = str(raw.get("name", "")).strip()
        if not name:
            raise ProbabilisticReasoningError("NODE_NAME_REQUIRED")
        states, prior = self._validate_node(raw)
        prior_type = str(raw.get("prior_type", "uniform"))
        if prior_type not in {"dirichlet", "uniform", "empirical"}:
            raise ProbabilisticReasoningError(f"INVALID_PRIOR_TYPE:{prior_type}")
        pseudo_counts = float(raw.get("pseudo_counts", 1.0))
        evidence_raw = raw.get("evidence")
        evidence = None
        if evidence_raw is not None:
            if not isinstance(evidence_raw, Mapping):
                raise ProbabilisticReasoningError(f"INVALID_EVIDENCE:{name}")
            evidence = {str(k): float(v) for k, v in evidence_raw.items()}

        dirichlet = self._posterior_dirichlet(prior, evidence, pseudo_counts, self.prior_strength)
        neural_result: dict[str, Any] | None = None

        neural_raw = raw.get("neural")
        if isinstance(neural_raw, Mapping):
            if "logits" in neural_raw:
                neural_result = self.neural.encode_logits(
                    neural_raw["logits"],
                    float(neural_raw.get("temperature", self.temperature)),
                )
            elif "vector" in neural_raw and "weights" in neural_raw:
                neural_result = self.neural.encode(
                    neural_raw["vector"],
                    neural_raw["weights"],
                    neural_raw.get("bias"),
                    float(neural_raw.get("temperature", self.temperature)),
                )
        elif raw.get("neural_logits") is not None:
            neural_result = self.neural.encode_logits(
                raw["neural_logits"],
                self.temperature,
            )

        if neural_result is None:
            posterior = dirichlet
            source = "dirichlet"
            entropy = self.neural.entropy(list(posterior))
        elif len(neural_result["probabilities"]) != len(states):
            raise ProbabilisticReasoningError(f"NEURAL_STATE_COUNT_MISMATCH:{name}")
        elif evidence is None:
            posterior = {
                state: probability
                for state, probability in zip(states, neural_result["probabilities"])
            }
            source = "neural"
            entropy = float(neural_result["entropy"])
        else:
            neural_probs = dict(zip(states, neural_result["probabilities"]))
            alpha = self.alpha_dirichlet
            beta = self.beta_neural
            if alpha == 0 and beta == 0:
                raise ProbabilisticReasoningError("ZERO_FUSION_WEIGHTS")
            fused = {
                state: (max(dirichlet[state], 1e-15) ** alpha)
                * (max(neural_probs[state], 1e-15) ** beta)
                for state in states
            }
            posterior = self._normalize(fused)
            source = "fused"
            entropy = self.neural.entropy(list(posterior))

        max_probability = max(posterior.values())
        if len(states) <= 1:
            confidence = 1.0
        else:
            confidence = max(0.0, min(1.0, 1.0 - entropy / math.log(len(states))))
        provenance = str(raw.get("provenance", "INFERRED"))
        if provenance not in {"HISTORICAL", "INFERRED", "USER", "TOOL"}:
            raise ProbabilisticReasoningError(f"INVALID_PROVENANCE:{name}")

        return BayesianNode(
            name=name,
            states=states,
            prior=prior,
            prior_type=prior_type,
            pseudo_counts=pseudo_counts,
            evidence=evidence,
            posterior=posterior,
            confidence=confidence,
            entropy=entropy,
            provenance=provenance,
            source=source,
        )

    def prepare(self, context: Mapping[str, Any] | None) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        if context is None:
            return None
        if not isinstance(context, Mapping):
            raise ProbabilisticReasoningError("CONTEXT_MUST_BE_OBJECT")
        payload = context.get("probabilistic")
        if payload is None:
            return None
        if not isinstance(payload, Mapping):
            raise ProbabilisticReasoningError("PROBABILISTIC_CONTEXT_MUST_BE_OBJECT")

        raw_nodes = payload.get("nodes")
        if not isinstance(raw_nodes, list):
            raise ProbabilisticReasoningError("NODES_REQUIRED")
        if len(raw_nodes) > 32:
            raise ProbabilisticReasoningError("TOO_MANY_NODES")

        nodes = [self._node(raw) for raw in raw_nodes if isinstance(raw, Mapping)]
        if len(nodes) != len(raw_nodes):
            raise ProbabilisticReasoningError("NODE_MUST_BE_OBJECT")
        node_names = {node.name for node in nodes}
        if len(node_names) != len(nodes):
            raise ProbabilisticReasoningError("DUPLICATE_NODE")

        structure_raw = payload.get("structure", {})
        if not isinstance(structure_raw, Mapping):
            raise ProbabilisticReasoningError("STRUCTURE_MUST_BE_OBJECT")
        structure = self._structure(structure_raw.get("edges"), node_names)
        if not structure.valid:
            raise ProbabilisticReasoningError("GRAPH_INVALID:" + "|".join(structure.validation_errors))

        interventions_raw = payload.get("interventions") or []
        if not isinstance(interventions_raw, list):
            raise ProbabilisticReasoningError("INTERVENTIONS_MUST_BE_LIST")
        interventions: list[dict[str, Any]] = []
        for raw in interventions_raw:
            if not isinstance(raw, Mapping):
                raise ProbabilisticReasoningError("INTERVENTION_MUST_BE_OBJECT")
            do = dict(raw.get("do") or {})
            evidence = dict(raw.get("evidence") or {})
            query = [str(v) for v in (raw.get("query") or [])]
            for node_name, state in {**do, **evidence}.items():
                if str(node_name) not in node_names:
                    raise ProbabilisticReasoningError(f"INTERVENTION_NODE_UNKNOWN:{node_name}")
                if str(state) not in next(node.states for node in nodes if node.name == str(node_name)):
                    raise ProbabilisticReasoningError(f"INTERVENTION_STATE_UNKNOWN:{node_name}:{state}")
            if any(str(v) not in node_names for v in query):
                raise ProbabilisticReasoningError("INTERVENTION_QUERY_NODE_UNKNOWN")
            interventions.append({
                "name": str(raw.get("name", f"intervention-{len(interventions)+1}")),
                "do": {str(k): str(v) for k, v in do.items()},
                "evidence": {str(k): str(v) for k, v in evidence.items()},
                "query": query,
            })

        fusion = {
            "alpha_dirichlet": self.alpha_dirichlet,
            "beta_neural": self.beta_neural,
            "temperature": self.temperature,
        }
        supplied_fusion = payload.get("fusion")
        if isinstance(supplied_fusion, Mapping):
            for key in fusion:
                if key in supplied_fusion:
                    fusion[key] = float(supplied_fusion[key])
            if fusion["alpha_dirichlet"] < 0 or fusion["beta_neural"] < 0 or fusion["temperature"] <= 0:
                raise ProbabilisticReasoningError("INVALID_FUSION_CONFIG")

        pipeline = {
            "steps": ["load", "clean", "normalize", "discretize", "bayes", "neural", "fuse", "gate"],
            "status": "ok",
            "warnings": [
                "causal_intervention_effects_require_conditional_tables"
            ] if interventions else [],
        }
        return {
            "structure": {
                "edges": [list(edge) for edge in structure.edges],
                "valid": structure.valid,
                "validation_errors": list(structure.validation_errors),
            },
            "nodes": [asdict(node) | {"states": list(node.states)} for node in nodes],
            "interventions": interventions or None,
            "fusion": fusion,
            "pipeline": pipeline,
            "feature_flag": "PROBABILISTIC_LAYER",
            "implementation": {
                "bayesian": "dirichlet_multinomial_laplace",
                "neural": "explicit_logits_or_linear_encoder",
                "training": "not_in_cycle",
                "pgmpy": "optional_adapter_not_loaded",
            },
        }
