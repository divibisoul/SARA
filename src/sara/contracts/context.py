"""SARA — Contexto de ciclo, evidência e rastreabilidade."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol
from sara.infra.clock import now_iso


@dataclass
class TraceSink:
    decision_trace: Any
    temporal: Any
    provenance: Any


@dataclass(frozen=True)
class CycleFusionState:
    """Estado verificado da fusão ARA/ETR/ITR/ERU em uma versão do ciclo."""
    cycle_id: str
    version: int
    target_hash: str
    ara_hash: str
    etr_hash: str
    itr_hash: str
    eru_snapshot_hashes: tuple[tuple[str, str], ...]
    fusion_snapshot_hash: str | None
    fused_hash: str
    integrity_ok: bool
    created_at: str = field(default_factory=now_iso)


@dataclass
class CycleStep:
    phase: str
    module: str
    ok: bool
    info: dict
    ts: str = field(default_factory=now_iso)


@dataclass
class CycleContext:
    cycle_id: str
    input: str
    current: str
    sink: TraceSink
    steps: list[CycleStep] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)
    fusion: CycleFusionState | None = None
    aborted: bool = False
    abort_reason: str = ""

    def record(self, phase: str, module: str, ok: bool, **info: Any) -> None:
        ts = now_iso()
        step = CycleStep(phase=phase, module=module, ok=ok, info=dict(info), ts=ts)
        self.steps.append(step)

        temporal_id = None
        if self.sink.temporal is not None:
            temporal_id = self.sink.temporal.insert({
                "cycle_id": self.cycle_id,
                "phase": phase,
                "module": module,
                "ok": ok,
                "info": info,
                "ts": ts,
            })
            step.info.setdefault("temporal_id", temporal_id)

        if self.sink.decision_trace is not None:
            entry = self.sink.decision_trace.log({
                "event": "cycle_step",
                "cycle_id": self.cycle_id,
                "phase": phase,
                "module": module,
                "ok": ok,
                "info": info,
                "ts": ts,
            })
            step.info.setdefault("decision_hash", entry.hash)

    def emit_decision(self, decision: dict) -> None:
        if self.sink.decision_trace is not None:
            self.sink.decision_trace.log({"cycle_id": self.cycle_id, **decision})

    def register_artifact(self, key: str, value: Any) -> None:
        self.artifacts[key] = value

    def abort(self, reason: str) -> None:
        self.aborted = True
        self.abort_reason = reason


class CycleContextProtocol(Protocol):
    cycle_id: str
    current: str
    sink: TraceSink
