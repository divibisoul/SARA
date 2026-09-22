"""SARA — Núcleo: Proveniência.
Status: IMPLEMENTED.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


class Provenance(str, Enum):
    HISTORICAL = "HISTORICAL"
    RECONSTRUCTED = "RECONSTRUCTED"
    INFERRED = "INFERRED"
    INVENTED = "INVENTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RuleProvenance:
    entity: str
    provenance: Provenance
    evidence: str
    source: Optional[str] = None


class ProvenanceTracker:
    NAME = "ProvenanceTracker"
    VERSION = "3.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.MEMORY
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.PERSISTENCE,)

    def __init__(self) -> None:
        self._rules: list[RuleProvenance] = []

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "records": len(self._rules),
        }

    def register(self, entity: str, provenance: Provenance,
                 evidence: str, source: Optional[str] = None) -> RuleProvenance:
        rp = RuleProvenance(entity, provenance, evidence, source)
        self._rules.append(rp)
        return rp

    def query(self, entity: str) -> list[RuleProvenance]:
        return [r for r in self._rules if r.entity == entity]

    def all(self) -> list[RuleProvenance]:
        return list(self._rules)

    def report(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self._rules:
            out[r.provenance.value] = out.get(r.provenance.value, 0) + 1
        return out

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("persistence", self.NAME, True, records=len(self._rules))
