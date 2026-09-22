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
        if min_aligned < 0:
            raise ValueError("min_aligned cannot be negative")
        results = self.classify(text)
        aligned = sum(1 for r in results if r.aligned)
        return {
            "passed": aligned >= min_aligned,
            "aligned_count": aligned,
            "required": min_aligned,
            "registered_filters": len(self._filters),
            "details": [r.__dict__ for r in results],
        }

    def evaluate_structured(self, text: str) -> dict:
        """Executa filtros com captura explícita de falhas e evidência."""
        results: list[dict] = []
        failures: list[str] = []
        for f in self._filters:
            try:
                result = f.evaluate(text)
                results.append(result.__dict__)
            except Exception as exc:
                failures.append(f"{type(f).__name__}:{type(exc).__name__}:{exc}")
        return {
            "ok": not failures,
            "results": results,
            "failures": failures,
            "filter_count": len(self._filters),
        }

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("validation", self.NAME, True,
                       filters=len(self._filters))