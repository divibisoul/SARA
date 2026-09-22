"""Bounded Bayesian-style readiness gate for ERU/SARA.

This is a decision aid, not a claim that the system has a mathematically
calibrated posterior over arbitrary engineering tasks. Inputs are explicit
evidence scores supplied by the caller.
"""
from __future__ import annotations
import math
from typing import Any


class BayesianMetaLearner:
    NAME = "BayesianMetaLearner"
    VERSION = "1.0"

    def __init__(self, confidence_threshold: float = 0.85) -> None:
        if not 0 < confidence_threshold < 1:
            raise ValueError("confidence_threshold deve estar entre 0 e 1")
        self.confidence_threshold = confidence_threshold

    @staticmethod
    def _logit(p: float) -> float:
        if not 0 < p < 1:
            raise ValueError("probabilidades devem estar entre 0 e 1")
        return math.log(p / (1.0 - p))

    def calculate_posterior_confidence(
        self, prior: float, likelihoods: list[float], evidence_weight: float = 1.0
    ) -> float:
        if evidence_weight < 0:
            raise ValueError("evidence_weight deve ser >= 0")
        posterior_logit = self._logit(prior)
        posterior_logit += evidence_weight * sum(self._logit(x) for x in likelihoods)
        posterior = 1.0 / (1.0 + math.exp(-posterior_logit))
        return round(posterior, 6)

    def evaluate(
        self,
        context_completeness: float,
        syntax_validity: float,
        historical_success_rate: float,
    ) -> dict[str, Any]:
        confidence = self.calculate_posterior_confidence(
            0.50,
            [context_completeness, syntax_validity, historical_success_rate],
        )
        return {
            "posterior_confidence": confidence,
            "threshold": self.confidence_threshold,
            "action_permitted": confidence >= self.confidence_threshold,
            "fallback_required": confidence < self.confidence_threshold,
            "evidence": {
                "context_completeness": context_completeness,
                "syntax_validity": syntax_validity,
                "historical_success_rate": historical_success_rate,
            },
            "calibration_status": "EXPLICIT_INPUTS_ONLY",
        }

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "threshold": self.confidence_threshold,
            "calibration_status": "EXPLICIT_INPUTS_ONLY",
        }
