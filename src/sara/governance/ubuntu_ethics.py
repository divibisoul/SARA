"""SARA — Governança: UbuntuEthics.
Status: IMPLEMENTED
"""
from __future__ import annotations
from dataclasses import dataclass
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


@dataclass(frozen=True)
class FilterResult:
    filter_name: str
    aligned: bool
    keywords_matched: tuple[str, ...]
    provenance: str = "ESPECIFICAÇÃO_HISTÓRICA_v5"


class UbuntuEthics:
    NAME = "UbuntuEthics"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.GOVERNANCE
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.VALIDATION,)

    PRINCIPLES = (
        "Eu sou porque nós somos",
        "Respeito à coletividade",
        "Cuidado com as gerações futuras",
    )
    KEYWORDS = ("coletivo", "comunidade", "nós", "gerações", "futuro")

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "principles_count": len(self.PRINCIPLES),
        }

    def evaluate(self, text: str) -> FilterResult:
        t = str(text).lower()
        hits = tuple(k for k in self.KEYWORDS if k in t)
        return FilterResult(
            filter_name="UbuntuEthics",
            aligned=len(hits) > 0,
            keywords_matched=hits,
        )

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("validation", self.NAME, True,
                       principles=len(self.PRINCIPLES))