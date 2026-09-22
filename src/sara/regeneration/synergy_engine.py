"""SARA — Regeneração: SynergyEngine v2.
Status: IMPLEMENTED (deep).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable
from sara.infra.clock import now_iso
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


@dataclass
class StageResult:
    stage: str
    ok: bool
    output: Any
    elapsed_ms: float
    error: str = ""


@dataclass
class PipelineReport:
    name: str
    stages: list[StageResult] = field(default_factory=list)
    ok: bool = True
    aborted_at: str = ""


class SynergyEngine:
    NAME = "SynergyEngine"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.REGENERATION
    DEPENDENCIES = ("CycleContext",)
    CYCLE_PHASES = (CyclePhase.REGENERATION,)

    def __init__(self) -> None:
        self._stages: dict[str, Callable[[Any, Any], Any]] = {}

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "stages_registered": list(self._stages.keys()),
        }

    def register_stage(self, name: str, fn: Callable[[Any, Any], Any]) -> None:
        if name in self._stages:
            raise ValueError(f"estágio '{name}' já registrado")
        self._stages[name] = fn

    def execute_pipeline(self, stage_names: list[str], input_data: Any,
                         ctx: Any = None, pipeline_name: str = "pipeline") -> PipelineReport:
        import time
        report = PipelineReport(name=pipeline_name)
        current = input_data
        for s in stage_names:
            fn = self._stages.get(s)
            if fn is None:
                report.ok = False
                report.aborted_at = s
                report.stages.append(StageResult(s, False, None, 0.0, "stage_unknown"))
                return report
            t0 = time.perf_counter()
            try:
                current = fn(current, ctx)
                elapsed = (time.perf_counter() - t0) * 1000
                report.stages.append(StageResult(s, True, current, elapsed))
                if ctx is not None and hasattr(ctx, "record"):
                    ctx.record("regeneration", f"synergy:{s}", True, elapsed_ms=elapsed)
            except Exception as exc:
                elapsed = (time.perf_counter() - t0) * 1000
                report.stages.append(StageResult(s, False, None, elapsed, str(exc)))
                report.ok = False
                report.aborted_at = s
                return report
        return report

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("regeneration", self.NAME, True,
                       stages_count=len(self._stages))