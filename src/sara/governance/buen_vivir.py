"""SARA — Governança: BuenVivir.
Status: IMPLEMENTED
"""
from __future__ import annotations
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.governance.ubuntu_ethics import FilterResult


class BuenVivir:
    NAME = "BuenVivir"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.GOVERNANCE
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.VALIDATION,)

    PRINCIPLES = (
        "Harmonia com a natureza",
        "Solidariedade comunitária",
        "Pluralidade de saberes",
    )
    KEYWORDS = ("natureza", "harmonia", "solidariedade", "pluralidade", "saberes")

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
            filter_name="BuenVivir",
            aligned=len(hits) > 0,
            keywords_matched=hits,
        )

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("validation", self.NAME, True,
                       principles=len(self.PRINCIPLES))