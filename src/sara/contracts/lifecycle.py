"""SARA — Ciclo de vida: fases canônicas.
Status: IMPLEMENTED (foundational).
"""
from __future__ import annotations
from sara.contracts.base import CyclePhase

CANONICAL_ORDER: tuple[CyclePhase, ...] = (
    CyclePhase.INGESTION,
    CyclePhase.AUDIT,
    CyclePhase.REGENERATION,
    CyclePhase.IDENTITY,
    CyclePhase.ETHICS,
    CyclePhase.STRATEGY,
    CyclePhase.EXECUTION,
    CyclePhase.VALIDATION,
    CyclePhase.PERSISTENCE,
    CyclePhase.SNAPSHOT,
    CyclePhase.MONITORING,
    CyclePhase.GOVERNANCE,
)