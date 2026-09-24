from __future__ import annotations

import os

from sara.bootstrap import build_default_system


def _context():
    return {
        "session_id": "session-001",
        "client": "web",
        "user_feedback_refs": ["feedback-001"],
        "probabilistic": {
            "structure": {"edges": []},
            "nodes": [{
                "name": "uncertainty",
                "states": ["low", "high"],
                "prior": {"low": 0.5, "high": 0.5},
                "pseudo_counts": 1.0,
                "evidence": {"high": 1.0},
                "provenance": "USER",
                "neural": {"logits": [0.0, 1.0]},
            }],
        },
    }


def test_probabilistic_layer_flag_off_preserves_legacy_path():
    old = os.environ.get("PROBABILISTIC_LAYER")
    os.environ.pop("PROBABILISTIC_LAYER", None)
    try:
        system = build_default_system(fail_closed=True)
        result = system.sistema_vivo.process(
            "preservar contexto",
            cycle_id="legacy-prob-off",
            context=_context(),
        )
        assert result.probabilistic is None
    finally:
        if old is not None:
            os.environ["PROBABILISTIC_LAYER"] = old


def test_probabilistic_layer_flows_to_cycle_artifacts_and_trace():
    old = os.environ.get("PROBABILISTIC_LAYER")
    os.environ["PROBABILISTIC_LAYER"] = "true"
    try:
        system = build_default_system(fail_closed=True)
        result = system.sistema_vivo.process(
            "preservar contexto",
            cycle_id="prob-federated-001",
            context=_context(),
        )
        assert result.probabilistic is not None
        node = result.probabilistic["nodes"][0]
        assert node["source"] == "fused"
        assert node["dirichlet_posterior"] is not None
        assert node["neural_posterior"] is not None
        assert "probabilistic" in result.loop_report.execution_report["artifacts"]
        assert "feedback_evidence_refs" in result.loop_report.execution_report["artifacts"]
        entries = system.components["trace"].query({"cycle_id": "prob-federated-001"})
        events = [entry.decision.get("event") for entry in entries]
        assert "probabilistic_context_prepared" in events
        assert "probabilistic_context_attached" in events
        assert "probabilistic_monitoring" in events
    finally:
        if old is None:
            os.environ.pop("PROBABILISTIC_LAYER", None)
        else:
            os.environ["PROBABILISTIC_LAYER"] = old
