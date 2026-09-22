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

    def record(self, phase: str, module: str, success: bool | None = None, **info: Any) -> None:
        """Registra uma etapa aceitando ok como metadado sem colisão."""
        if success is None and "ok" in info:
            success = bool(info.pop("ok"))
        if success is None:
            raise TypeError("CycleContext.record requer sucesso explícito")
        ok = bool(success)
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
            # O payload enviado ao trace precisa ser independente do dicionário
            # que continuará sendo enriquecido com temporal_id/decision_hash.
            trace_info = dict(info)
            entry = self.sink.decision_trace.log({
                "event": "cycle_step",
                "cycle_id": self.cycle_id,
                "phase": phase,
                "module": module,
                "ok": ok,
                "info": trace_info,
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
