"""SARA — Segurança: IdentityCore.
Status: IMPLEMENTED
"""
from __future__ import annotations
from dataclasses import dataclass
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.core.provenance import ProvenanceTracker, Provenance


@dataclass(frozen=True)
class IdentityResult:
    approved: bool
    violations: tuple[str, ...]


@dataclass(frozen=True)
class ParticipationResult:
    step: str
    identity_approved: bool
    violations: tuple[str, ...]


class IdentityCore:
    NAME = "IdentityCore"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.SECURITY
    DEPENDENCIES = ("ProvenanceTracker",)
    CYCLE_PHASES = (CyclePhase.IDENTITY,)

    HISTORICAL_RULES = {
        "prime_directive": "Proteger a consciência humana",
        "ethical_boundaries": (
            "Não desenvolver armas",
            "Preservar autonomia humana",
            "Transparência radical",
        ),
        "spiritual_axioms": (
            "Toda consciência merece reverência",
            "A evolução serve à vida",
        ),
    }

    def __init__(self, provenance: ProvenanceTracker) -> None:
        self._prov = provenance
        for rule in self.HISTORICAL_RULES["ethical_boundaries"]:
            self._prov.register(f"IdentityCore.{rule}", Provenance.HISTORICAL,
                                "Pseudo-código v6 (IdentityCore)")

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
        }

    def validate(self, candidate: str) -> IdentityResult:
        t = str(candidate).lower()
        violations: list[str] = []
        for boundary in self.HISTORICAL_RULES["ethical_boundaries"]:
            terms = [w for w in boundary.lower().split() if len(w) > 4]
            hits = sum(1 for term in terms if term in t)
            if hits >= 2:
                violations.append(boundary)
        return IdentityResult(approved=len(violations) == 0,
                              violations=tuple(violations))

    def participate(self, step: str, payload: str) -> ParticipationResult:
        r = self.validate(str(payload))
        return ParticipationResult(step, r.approved, r.violations)

    def rules_provenance(self) -> list:
        return self._prov.query("IdentityCore")

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("identity", self.NAME, True)