"""SARA — Segurança: EthicalFilterChain.
Status: IMPLEMENTED
"""
from __future__ import annotations
from typing import Protocol
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.governance.ubuntu_ethics import FilterResult


class EthicalFilter(Protocol):
    def evaluate(self, text: str) -> FilterResult: ...


class EthicalFilterChain:
    NAME = "EthicalFilterChain"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.SECURITY
    DEPENDENCIES = ("UbuntuEthics", "BuenVivir")
    CYCLE_PHASES = (CyclePhase.VALIDATION,)

    def __init__(self) -> None:
        self._filters: list[EthicalFilter] = []

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "filters_registered": len(self._filters),
        }

    def register(self, f: EthicalFilter) -> None:
        self._filters.append(f)

    def classify(self, text: str) -> list[FilterResult]:
        return [f.evaluate(text) for f in self._filters]

    def as_gate(self, text: str, min_aligned: int = 1) -> dict:
        results = self.classify(text)
        aligned = sum(1 for r in results if r.aligned)
        return {
            "passed": aligned >= min_aligned,
            "aligned_count": aligned,
            "details": [r.__dict__ for r in results],
        }

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("validation", self.NAME, True,
                       filters=len(self._filters))