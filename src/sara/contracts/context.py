"""SARA — Contexto de Ciclo (CycleContext).
Status: IMPLEMENTED (foundational).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional
from sara.infra.clock import now_iso


@dataclass
class TraceSink:
    decision_trace: Any
    temporal: Any
    provenance: Any


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
    aborted: bool = False
    abort_reason: str = ""

    def record(self, phase: str, module: str, ok: bool, **info: Any) -> None:
        step = CycleStep(phase=phase, module=module, ok=ok, info=dict(info))
        self.steps.append(step)
        if self.sink.temporal is not None:
            self.sink.temporal.insert({
                "cycle_id": self.cycle_id,
                "phase": phase,
                "module": module,
                "ok": ok,
                "info": info,
            })

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