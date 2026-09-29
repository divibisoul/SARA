from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from sara.omega.models import ETRContext, ETRMetric, utc_now
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


@dataclass
class HabitObservation:
    key: str
    count: int = 0
    last_seen: str = ""


class HabitLearningEngine:
    NAME = "HabitLearningEngine"
    def __init__(self) -> None:
        self._patterns: dict[str, HabitObservation] = {}

    def observe(self, key: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        key = str(key).strip()
        if not key:
            raise ValueError("habit_key_empty")
        item = self._patterns.setdefault(key, HabitObservation(key))
        item.count += 1
        item.last_seen = utc_now()
        return {"key": key, "count": item.count, "context": dict(context or {})}

    def predict(self, candidates: list[str]) -> list[dict[str, Any]]:
        return sorted(
            [{"key": c, "count": self._patterns.get(c, HabitObservation(c)).count}
             for c in candidates],
            key=lambda x: x["count"], reverse=True,
        )


class AnticipationEngine:
    NAME = "AnticipationEngine"
    def anticipate(self, context: dict[str, Any]) -> dict[str, Any]:
        battery = context.get("battery_percent")
        network = context.get("network")
        hour = context.get("hour")
        recommendations = []
        if isinstance(battery, (int, float)) and battery <= 20:
            recommendations.append("reduce_optional_work")
        if network == "offline":
            recommendations.append("defer_network_work")
        if isinstance(hour, int) and 0 <= hour < 6:
            recommendations.append("prefer_background_safe_work")
        return {"recommendations": recommendations, "evidence": dict(context)}


class MicroMacroManager:
    """Escala micro/mid/macro explicitamente, sem atribuir política de parada implícita."""

    NAME = "MicroMacroManager"
    VERSION = "1.1"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.AUDIT, CyclePhase.EXECUTION, CyclePhase.MONITORING, CyclePhase.PERSISTENCE)
    STATES = ("MICRO", "MID", "MACRO")

    def __init__(self) -> None:
        self.state = "MICRO"
        self.completed = 0
        self._observations: list[dict[str, Any]] = []

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME, "version": self.VERSION, "status": self.STATUS.value,
            "role": self.ROLE.value, "dependencies": list(self.DEPENDENCIES),
            "phases": [x.value for x in self.CYCLE_PHASES],
            "state": self.state, "completed": self.completed,
            "observations": len(self._observations),
        }

    def transition_explicit(self, state: str, *, evidence: dict[str, Any]) -> str:
        state = str(state).strip().upper()
        if state not in self.STATES:
            raise ValueError("MMD_INVALID_STATE")
        if not isinstance(evidence, dict) or not evidence:
            raise ValueError("MMD_EVIDENCE_REQUIRED")
        self.state = state
        self._observations.append({
            "kind": "explicit_transition",
            "state": state,
            "evidence": dict(evidence),
            "ts": utc_now(),
        })
        return self.state

    def observe_scale(self, state: str, *, evidence: dict[str, Any]) -> dict[str, Any]:
        self.transition_explicit(state, evidence=evidence)
        return {
            "state": self.state,
            "evidence": dict(evidence),
            "observation_index": len(self._observations) - 1,
        }

    def observation_count(self) -> int:
        return len(self._observations)

    def transition(self, *, health_score: float, completed: int | None = None) -> str:
        # Compatibility path for the existing Omega implementation. Its previous
        # health-driven behavior remains available, while new integrations use
        # transition_explicit so no implicit threshold becomes an RGO policy.
        if completed is not None:
            self.completed = max(0, int(completed))
        score = max(0.0, min(1.0, float(health_score)))
        target = "MACRO" if score >= 0.9 and self.completed >= 10 else "MID" if score >= 0.7 else "MICRO"
        self.state = target
        self._observations.append({
            "kind": "compatibility_health_transition",
            "state": target,
            "health_score": score,
            "completed": self.completed,
            "ts": utc_now(),
        })
        return self.state

    def emit_trace(self, ctx: Any) -> None:
        if hasattr(ctx, "record"):
            ctx.record(
                "monitoring", self.NAME, True,
                state=self.state, completed=self.completed,
                observations=len(self._observations),
            )
