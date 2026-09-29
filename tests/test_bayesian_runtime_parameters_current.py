import math
import unittest

from sara.meta import BayesianMetaLearner, BayesianParameters, ERURuntime


class BayesianRuntimeTests(unittest.TestCase):
    def test_bayesian_parameters_are_first_class(self):
        params = BayesianParameters(prior=0.60, evidence_weight=0.5, confidence_threshold=0.80)
        learner = BayesianMetaLearner(
            confidence_threshold=params.confidence_threshold,
            prior=params.prior,
            evidence_weight=params.evidence_weight,
        )
        description = learner.describe()
        self.assertEqual(description["version"], "1.1")
        self.assertEqual(description["prior"], 0.60)
        self.assertEqual(description["evidence_weight"], 0.5)
        self.assertEqual(description["threshold"], 0.80)

        result = learner.evaluate(0.95, 0.95, 0.90)
        self.assertEqual(
            result["parameters"],
            {"prior": 0.60, "evidence_weight": 0.5, "confidence_threshold": 0.80},
        )

    def test_bayesian_sigmoid_is_numerically_stable(self):
        learner = BayesianMetaLearner()
        self.assertTrue(math.isfinite(learner._sigmoid(-1000.0)))
        self.assertEqual(learner._sigmoid(-1000.0), 0.0)

    def test_eru_runtime_exposes_bayesian_runtime_state(self):
        runtime = ERURuntime(prior=0.55, evidence_weight=0.75, confidence_threshold=0.82)
        description = runtime.describe()
        self.assertEqual(description["version"], "1.1")
        self.assertEqual(description["meta_learner"]["prior"], 0.55)
        self.assertEqual(description["meta_learner"]["evidence_weight"], 0.75)


if __name__ == "__main__":
    unittest.main()
