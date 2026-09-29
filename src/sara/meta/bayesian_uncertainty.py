"""Bounded Bayesian-style readiness gate for ERU/SARA.

This is a decision aid, not a claim that the system has a mathematically
calibrated posterior over arbitrary engineering tasks. Inputs are explicit
evidence scores supplied by the caller.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Any


@dataclass(frozen=True)
class BayesianParameters:
    """Parâmetros explícitos e de primeira classe do estimador bayesiano limitado."""

    prior: float = 0.50
    evidence_weight: float = 1.0
    confidence_threshold: float = 0.85

    def __post_init__(self) -> None:
        if not math.isfinite(self.prior) or not 0 < self.prior < 1:
            raise ValueError("prior deve estar entre 0 e 1")
        if not math.isfinite(self.evidence_weight) or self.evidence_weight < 0:
            raise ValueError("evidence_weight deve ser finito e >= 0")
        if not math.isfinite(self.confidence_threshold) or not 0 < self.confidence_threshold < 1:
            raise ValueError("confidence_threshold deve estar entre 0 e 1")


class BayesianMetaLearner:
    NAME = "BayesianMetaLearner"
    VERSION = "1.1"

    def __init__(
        self,
        confidence_threshold: float = 0.85,
        *,
        prior: float = 0.50,
        evidence_weight: float = 1.0,
    ) -> None:
        self.parameters = BayesianParameters(
            prior=prior,
            evidence_weight=evidence_weight,
            confidence_threshold=confidence_threshold,
        )
        self.confidence_threshold = self.parameters.confidence_threshold

    @staticmethod
    def _logit(p: float) -> float:
        if not math.isfinite(p) or not 0 < p < 1:
            raise ValueError("probabilidades devem estar entre 0 e 1")
        return math.log(p / (1.0 - p))

    @staticmethod
    def _sigmoid(logit: float) -> float:
        if not math.isfinite(logit):
            raise ValueError("logit deve ser finito")
        if logit >= 0:
            z = math.exp(-logit)
            return 1.0 / (1.0 + z)
        z = math.exp(logit)
        return z / (1.0 + z)

    def calculate_posterior_confidence(
        self, prior: float, likelihoods: list[float], evidence_weight: float = 1.0
    ) -> float:
        if not math.isfinite(evidence_weight) or evidence_weight < 0:
            raise ValueError("evidence_weight deve ser >= 0")
        posterior_logit = self._logit(prior)
        posterior_logit += evidence_weight * sum(self._logit(x) for x in likelihoods)
        posterior = self._sigmoid(posterior_logit)
        return round(posterior, 6)

    def evaluate(
        self,
        context_completeness: float,
        syntax_validity: float,
        historical_success_rate: float,
    ) -> dict[str, Any]:
        confidence = self.calculate_posterior_confidence(
            self.parameters.prior,
            [context_completeness, syntax_validity, historical_success_rate],
            self.parameters.evidence_weight,
        )
        return {
            "posterior_confidence": confidence,
            "threshold": self.confidence_threshold,
            "prior": self.parameters.prior,
            "evidence_weight": self.parameters.evidence_weight,
            "action_permitted": confidence >= self.confidence_threshold,
            "fallback_required": confidence < self.confidence_threshold,
            "evidence": {
                "context_completeness": context_completeness,
                "syntax_validity": syntax_validity,
                "historical_success_rate": historical_success_rate,
            },
            "parameters": {
                "prior": self.parameters.prior,
                "evidence_weight": self.parameters.evidence_weight,
                "confidence_threshold": self.parameters.confidence_threshold,
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
