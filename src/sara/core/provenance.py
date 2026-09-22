"""SARA — Núcleo: Proveniência.
Status: IMPLEMENTED
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional


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
    def __init__(self) -> None:
        self._rules: list[RuleProvenance] = []

    def register(
        self,
        entity: str,
        provenance: Provenance,
        evidence: str,
        source: Optional[str] = None,
    ) -> RuleProvenance:
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