from __future__ import annotations

import os

from sara.bootstrap import build_default_system


def test_sara_cycle_accepts_and_traces_probabilistic_context():
    old = os.environ.get("PROBABILISTIC_LAYER")
    os.environ["PROBABILISTIC_LAYER"] = "true"
    try:
        system = build_default_system(fail_closed=True)
        result = system.sistema_vivo.process(
            "preservar autonomia e validar contexto",
            cycle_id="prob-test-001",
            context={
                "session_id": "session-prob-001",
                "client": "web",
                "user_feedback_refs": ["feedback-001"],
                "probabilistic": {
                    "structure": {"edges": []},
                    "nodes": [{
                        "name": "uncertainty",
                        "states": ["low", "high"],
                        "prior": {"low": 0.5, "high": 0.5},
                        "prior_type": "dirichlet",
                        "pseudo_counts": 1.0,
                        "evidence": {"high": 2.0},
                        "provenance": "USER",
                        "neural": {"logits": [0.0, 1.0]},
                    }],
                },
            },
        )
        assert result.probabilistic is not None
        node = result.probabilistic["nodes"][0]
        assert node["source"] == "fused"
        assert 0.0 <= node["confidence"] <= 1.0
        assert "probabilistic" in result.loop_report.execution_report["artifacts"]

        entries = system.components["trace"].query({"cycle_id": "prob-test-001"})
        events = [entry.decision.get("event") for entry in entries]
        assert "probabilistic_context_prepared" in events
        assert "probabilistic_context_attached" in events
        assert "probabilistic_monitoring" in events
    finally:
        if old is None:
            os.environ.pop("PROBABILISTIC_LAYER", None)
        else:
            os.environ["PROBABILISTIC_LAYER"] = old


def test_sara_probabilistic_invalid_graph_is_deterministic_failure():
    old = os.environ.get("PROBABILISTIC_LAYER")
    os.environ["PROBABILISTIC_LAYER"] = "true"
    try:
        system = build_default_system(fail_closed=True)
        try:
            system.sistema_vivo.prepare_context({
                "probabilistic": {
                    "structure": {"edges": [["a", "b"], ["b", "a"]]},
                    "nodes": [
                        {
                            "name": "a",
                            "states": ["x"],
                            "prior": {"x": 1.0},
                            "pseudo_counts": 1.0,
                        },
                        {
                            "name": "b",
                            "states": ["x"],
                            "prior": {"x": 1.0},
                            "pseudo_counts": 1.0,
                        },
                    ],
                }
            })
        except ValueError as exc:
            assert "GRAPH_INVALID" in str(exc)
        else:
            raise AssertionError("invalid graph must fail deterministically")
    finally:
        if old is None:
            os.environ.pop("PROBABILISTIC_LAYER", None)
        else:
            os.environ["PROBABILISTIC_LAYER"] = old
