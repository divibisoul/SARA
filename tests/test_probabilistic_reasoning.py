

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

def test_fusion_payload_overrides_defaults():
    layer = ProbabilisticReasoningLayer(enabled=True)
    result = layer.prepare({
        "probabilistic": {
            "fusion": {
                "alpha_dirichlet": 1.0,
                "beta_neural": 0.0,
                "temperature": 1.0,
            },
            "nodes": [node(evidence={"high": 2.0}, neural={"logits": [100.0, -100.0]})],
        }
    })
    posterior = result["nodes"][0]["posterior"]
    expected = result["nodes"][0]["prior"]
    assert posterior == expected