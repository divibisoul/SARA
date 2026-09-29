import math

from sara.meta import BayesianMetaLearner, BayesianParameters, ERURuntime


def test_bayesian_parameters_are_first_class():
    params = BayesianParameters(prior=0.60, evidence_weight=0.5, confidence_threshold=0.80)
    learner = BayesianMetaLearner(
        confidence_threshold=params.confidence_threshold,
        prior=params.prior,
        evidence_weight=params.evidence_weight,
    )
    description = learner.describe()
    assert description["version"] == "1.1"
    assert description["prior"] == 0.60
    assert description["evidence_weight"] == 0.5
    assert description["threshold"] == 0.80

    result = learner.evaluate(0.95, 0.95, 0.90)
    assert result["parameters"] == {
        "prior": 0.60,
        "evidence_weight": 0.5,
        "confidence_threshold": 0.80,
    }


def test_bayesian_sigmoid_is_numerically_stable():
    learner = BayesianMetaLearner()
    assert math.isfinite(learner._sigmoid(-1000.0))
    assert learner._sigmoid(-1000.0) == 0.0


def test_eru_runtime_exposes_bayesian_runtime_state():
    runtime = ERURuntime(prior=0.55, evidence_weight=0.75, confidence_threshold=0.82)
    description = runtime.describe()
    assert description["version"] == "1.1"
    assert description["meta_learner"]["prior"] == 0.55
    assert description["meta_learner"]["evidence_weight"] == 0.75
