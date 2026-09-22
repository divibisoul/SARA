from __future__ import annotations

import math

import pytest

from sara.probabilistic import (
    ContinuousToDiscrete,
    NeuralProbEncoder,
    ProbabilisticReasoningError,
    ProbabilisticReasoningLayer,
)


def node(name="risk", evidence=None, neural=None):
    payload = {
        "name": name,
        "states": ["low", "high"],
        "prior": {"low": 0.5, "high": 0.5},
        "prior_type": "dirichlet",
        "pseudo_counts": 1.0,
        "provenance": "USER",
    }
    if evidence is not None:
        payload["evidence"] = evidence
    if neural is not None:
        payload["neural"] = neural
    return payload


def test_flag_off_is_skipped():
    layer = ProbabilisticReasoningLayer(enabled=False)
    assert layer.prepare({"probabilistic": {"nodes": []}}) is None


def test_dirichlet_posterior_is_real_and_normalized():
    layer = ProbabilisticReasoningLayer(enabled=True)
    result = layer.prepare({
        "probabilistic": {
            "structure": {"edges": []},
            "nodes": [node(evidence={"high": 3.0})],
        }
    })
    posterior = result["nodes"][0]["posterior"]
    assert math.isclose(sum(posterior.values()), 1.0)
    assert posterior["high"] > posterior["low"]
    assert result["nodes"][0]["source"] == "dirichlet"


def test_neural_only_uses_calibrated_softmax():
    layer = ProbabilisticReasoningLayer(enabled=True, temperature=2.0)
    result = layer.prepare({
        "probabilistic": {
            "nodes": [node(neural={"logits": [0.0, 2.0], "temperature": 2.0})],
        }
    })
    item = result["nodes"][0]
    assert item["source"] == "neural"
    assert item["posterior"]["high"] < 0.9
    assert 0.0 <= item["confidence"] <= 1.0


def test_fusion_reports_fused_source():
    layer = ProbabilisticReasoningLayer(enabled=True)
    result = layer.prepare({
        "probabilistic": {
            "nodes": [node(evidence={"high": 2.0}, neural={"logits": [0.0, 2.0]})],
        }
    })
    assert result["nodes"][0]["source"] == "fused"


def test_cyclic_graph_fails_closed():
    layer = ProbabilisticReasoningLayer(enabled=True)
    with pytest.raises(ProbabilisticReasoningError, match="GRAPH_INVALID"):
        layer.prepare({
            "probabilistic": {
                "structure": {"edges": [["a", "b"], ["b", "a"]]},
                "nodes": [node("a"), node("b")],
            }
        })


def test_intervention_nodes_are_validated_without_fake_causal_effect():
    layer = ProbabilisticReasoningLayer(enabled=True)
    result = layer.prepare({
        "probabilistic": {
            "structure": {"edges": []},
            "nodes": [node()],
            "interventions": [{
                "name": "test",
                "do": {"risk": "high"},
                "evidence": {"risk": "high"},
                "query": ["risk"],
            }],
        }
    })
    assert result["interventions"][0]["name"] == "test"
    assert "causal_intervention_effects_require_conditional_tables" in result["pipeline"]["warnings"]


def test_continuous_to_discrete():
    discretizer = ContinuousToDiscrete({"score": [0.3, 0.7]})
    assert discretizer.transform("score", 0.2, ["low", "mid", "high"]) == "low"
    assert discretizer.transform("score", 0.5, ["low", "mid", "high"]) == "mid"
    assert discretizer.transform("score", 0.9, ["low", "mid", "high"]) == "high"


def test_neural_vector_encoder_is_deterministic():
    encoder = NeuralProbEncoder()
    one = encoder.encode([1.0, 2.0], [[1.0, 0.0], [0.0, 1.0]])
    two = encoder.encode([1.0, 2.0], [[1.0, 0.0], [0.0, 1.0]])
    assert one == two
