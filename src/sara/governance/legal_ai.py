"""SARA — Governança: LegalAI.
Status: IMPLEMENTED (cadeia local) | PENDING_INFRASTRUCTURE (blockchain, patentes)
"""
from __future__ import annotations
from dataclasses import dataclass
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.hashing import chain_hash
from sara.infra.clock import now_iso


@dataclass
class LegalDecision:
    tech: str
    license: str
    approved: bool
    ts: str
    prev_hash: str
    hash: str


class LegalAI:
    NAME = "LegalAI"
    VERSION = "2.0"
    STATUS = ModuleStatus.PENDING_INFRASTRUCTURE
    ROLE = CycleRole.GOVERNANCE
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.GOVERNANCE,)

    def __init__(self, allowed_licenses: set[str]) -> None:
        self._allowed = set(allowed_licenses)
        self._chain: list[LegalDecision] = []

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "chain_length": len(self._chain),
            "patent_oracle_ready": self.is_patent_oracle_ready(),
        }

    def is_patent_oracle_ready(self) -> bool:
        return False

    def validate_license(self, tech_name: str, license_id: str) -> LegalDecision:
        prev = self._chain[-1].hash if self._chain else "GENESIS"
        approved = license_id in self._allowed
        payload = {"tech": tech_name, "license": license_id, "approved": approved}
        h = chain_hash(prev, payload)
        d = LegalDecision(tech_name, license_id, approved, now_iso(), prev, h)
        self._chain.append(d)
        return d

    def check_patent(self, tech_name: str, jurisdiction: str) -> dict:
        raise NotImplementedError(
            "LegalAI.check_patent requer integração com bases de patentes reais "
            "(USPTO, INPI, EPO) ou oracle de patentes. Nenhuma API está disponível. "
            "Ativação: ver CANONICAL_ACTIVATION_PLAN.for_module('LegalAI')."
        )

    def verify_chain(self) -> bool:
        prev = "GENESIS"
        for d in self._chain:
            expected = chain_hash(prev, {"tech": d.tech, "license": d.license, "approved": d.approved})
            if expected != d.hash:
                return False
            prev = d.hash
        return True

    def chain(self) -> list[LegalDecision]:
        return list(self._chain)

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, True,
                       chain_length=len(self._chain),
                       chain_valid=self.verify_chain())