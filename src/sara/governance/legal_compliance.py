"""SARA — Governança: LegalCompliance.
Status: IMPLEMENTED
"""
from __future__ import annotations
from dataclasses import dataclass
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


@dataclass(frozen=True)
class ComplianceResult:
    approved: bool
    license: str
    reason: str


DEFAULT_ALLOWED = {"MIT", "Apache-2.0", "BSD-3-Clause"}


class LegalCompliance:
    NAME = "LegalCompliance"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.GOVERNANCE
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.GOVERNANCE,)

    def __init__(self, allowed: set[str] | None = None) -> None:
        self._allowed: set[str] = set(allowed or DEFAULT_ALLOWED)
        self._registry: dict[str, dict] = {}

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "allowed_count": len(self._allowed),
        }

    def register_license(self, license_id: str, terms: dict) -> None:
        self._registry[license_id] = dict(terms)
        if terms.get("permissive"):
            self._allowed.add(license_id)

    def validate(self, tech_license: str, context: dict | None = None) -> ComplianceResult:
        if tech_license in self._allowed:
            return ComplianceResult(True, tech_license, "permitida")
        return ComplianceResult(False, tech_license, "não permitida")

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, True,
                       allowed_count=len(self._allowed))