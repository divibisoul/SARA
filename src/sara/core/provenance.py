"""SARA — Núcleo: Proveniência.
Status: IMPLEMENTED.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import threading
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.hashing import chain_hash


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
    hash: str = ""


class ProvenanceTracker:
    NAME = "ProvenanceTracker"
    VERSION = "3.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.MEMORY
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.PERSISTENCE,)

    def __init__(self) -> None:
        self._rules: list[RuleProvenance] = []
        self._chain: list[str] = []
        self._lock = threading.RLock()

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "records": len(self._rules),
            "integrity": self.verify_integrity(),
            "integrity_head": self.integrity_head(),
        }

    def register(self, entity: str, provenance: Provenance,
                 evidence: str, source: Optional[str] = None) -> RuleProvenance:
        with self._lock:
            previous = self._chain[-1] if self._chain else "GENESIS"
            payload = {
                "entity": entity,
                "provenance": provenance.value,
                "evidence": evidence,
                "source": source,
            }
            current = chain_hash(previous, payload)
            rp = RuleProvenance(entity, provenance, evidence, source, current)
            self._rules.append(rp)
            self._chain.append(current)
            return rp

    def query(self, entity: str) -> list[RuleProvenance]:
        with self._lock:
            return [r for r in self._rules if r.entity == entity]

    def all(self) -> list[RuleProvenance]:
        with self._lock:
            return list(self._rules)

    def verify_integrity(self) -> bool:
        with self._lock:
            if len(self._rules) != len(self._chain):
                return False
            previous = "GENESIS"
            for rule, chain_value in zip(self._rules, self._chain):
                payload = {
                    "entity": rule.entity,
                    "provenance": rule.provenance.value,
                    "evidence": rule.evidence,
                    "source": rule.source,
                }
                expected = chain_hash(previous, payload)
                if expected != chain_value or rule.hash != chain_value:
                    return False
                previous = chain_value
            return True

    def integrity_head(self) -> str:
        with self._lock:
            return self._chain[-1] if self._chain else "GENESIS"

    def report(self) -> dict[str, int]:
        out: dict[str, int] = {}
        with self._lock:
            for r in self._rules:
                out[r.provenance.value] = out.get(r.provenance.value, 0) + 1
            return out

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("persistence", self.NAME, True, records=len(self._rules), integrity=self.verify_integrity())
