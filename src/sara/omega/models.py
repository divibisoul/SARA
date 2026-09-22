from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ETRMetric:
    name: str
    value: float
    unit: str
    source: str
    observed_at: str
    confidence: float = 1.0


@dataclass(frozen=True)
class ETRContext:
    cycle_id: str
    metrics: tuple[ETRMetric, ...]
    facts: dict[str, Any] = field(default_factory=dict)
    previous: dict[str, Any] = field(default_factory=dict)

    def metric(self, name: str) -> ETRMetric | None:
        return next((m for m in self.metrics if m.name == name), None)


@dataclass(frozen=True)
class ETRReport:
    nucleus: str
    ok: bool
    findings: tuple[dict[str, Any], ...]
    metrics: tuple[ETRMetric, ...] = ()
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ETRAction:
    id: str
    kind: str
    description: str
    impact: float
    urgency: float
    cost: float
    reversible: bool
    execute: Callable[[], dict[str, Any]]
    rollback: Callable[[], dict[str, Any]]


@dataclass(frozen=True)
class ETRPlan:
    plan_id: str
    actions: tuple[ETRAction, ...]
    rationale: tuple[str, ...]
    generated_at: str


@dataclass(frozen=True)
class ETRResult:
    action_id: str
    ok: bool
    output: dict[str, Any]
    rolled_back: bool = False
    rollback_output: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OmegaCycleReport:
    cycle_id: str
    ok: bool
    analysis: tuple[ETRReport, ...]
    plan: ETRPlan
    results: tuple[ETRResult, ...]
    adaptation: dict[str, Any]
    evidence: dict[str, Any]
