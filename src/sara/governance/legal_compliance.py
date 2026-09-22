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
        license_id = str(tech_license).strip()
        if not license_id:
            return ComplianceResult(False, license_id, "licença ausente")
        terms = self._registry.get(license_id, {})
        if license_id in self._allowed:
            if context and context.get("commercial_use") and terms.get("non_commercial"):
                return ComplianceResult(False, license_id, "restrição non_commercial incompatível")
            return ComplianceResult(True, license_id, "permitida")
        return ComplianceResult(False, license_id, "não permitida")

    def explain(self, tech_license: str, context: dict | None = None) -> dict:
        result = self.validate(tech_license, context=context)
        return {
            "approved": result.approved,
            "license": result.license,
            "reason": result.reason,
            "registered_terms": dict(self._registry.get(result.license, {})),
            "context": dict(context or {}),
        }

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, True,
                       allowed_count=len(self._allowed))