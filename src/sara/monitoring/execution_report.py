"""SARA — deterministic execution report assembled from real cycle evidence."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from sara.infra.hashing import hash_json


@dataclass
class PhaseEvidence:
    phase: str
    module: str
    ok: bool
    info: dict[str, Any]
    ts: str


@dataclass
class ExecutionReport:
    cycle_id: str
    status: str
    phases: list[PhaseEvidence] = field(default_factory=list)
    invariants: list[dict] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    trace_integrity: bool = False
    evidence_hash: str = ""

    def finalize(self) -> "ExecutionReport":
        payload = {
            "cycle_id": self.cycle_id,
            "status": self.status,
            "phases": [
                {"phase": p.phase, "module": p.module, "ok": p.ok, "info": p.info, "ts": p.ts}
                for p in self.phases
            ],
            "invariants": self.invariants,
            "artifacts": self.artifacts,
            "trace_integrity": self.trace_integrity,
        }
        self.evidence_hash = hash_json(payload)
        return self

    def as_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "status": self.status,
            "phases": [
                {"phase": p.phase, "module": p.module, "ok": p.ok, "info": p.info, "ts": p.ts}
                for p in self.phases
            ],
            "invariants": self.invariants,
            "artifacts": self.artifacts,
            "trace_integrity": self.trace_integrity,
            "evidence_hash": self.evidence_hash,
        }
