from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sara.omega.models import ETRContext, ETRMetric, utc_now


@dataclass
class HabitObservation:
    key: str
    count: int = 0
    last_seen: str = ""


class HabitLearningEngine:
    """Aprende apenas de observações explicitamente fornecidas ao runtime.

    Não presume acesso a Android UsageStats quando está rodando no SARA Python.
    """
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
    NAME = "MicroMacroManager"
    STATES = ("MICRO", "MID", "MACRO")
    def __init__(self) -> None:
        self.state = "MICRO"
        self.completed = 0
    def transition(self, *, health_score: float, completed: int | None = None) -> str:
        if completed is not None:
            self.completed = max(0, int(completed))
        score = max(0.0, min(1.0, float(health_score)))
        target = "MACRO" if score >= 0.9 and self.completed >= 10 else "MID" if score >= 0.7 else "MICRO"
        self.state = target
        return self.state
