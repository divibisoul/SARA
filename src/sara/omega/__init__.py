"""SARA Omega — camada aditiva Soul + ETR-Genesis adaptada ao runtime SARA.

A camada não substitui ARA/ETR/ITR/ERU. Ela fornece análise operacional,
detecção de assimetrias, entropia, validação de realidade, planejamento,
priorização, execução reversível e adaptação por feedback real.
"""
from sara.omega.models import (
    ETRContext, ETRMetric, ETRReport, ETRPlan, ETRAction,
    ETRResult, OmegaCycleReport,
)
from sara.omega.system import SoulETROmegaSystem

__all__ = [
    "ETRContext", "ETRMetric", "ETRReport", "ETRPlan", "ETRAction",
    "ETRResult", "OmegaCycleReport", "SoulETROmegaSystem",
]
