"""SARA — Meta: ERU drift detector.
Status: IMPLEMENTED — métricas estruturais derivadas dos snapshots da ERU.
"""
from __future__ import annotations

from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.meta.eru_engine import ERU_Engine


class ERUDriftDetector:
    NAME = "ERUDriftDetector"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = ("ERU_Engine",)
    CYCLE_PHASES = (CyclePhase.AUDIT,)

    def __init__(self, eru: ERU_Engine) -> None:
        self._eru = eru

    def describe(self) -> dict:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
        }

    def compute_drift(self, older: str, newer: str) -> dict:
        diff = self._eru.compare(older, newer)
        lost = len(diff.lost)
        added = len(diff.added)
        changed = len(diff.changed)
        kept = len(diff.kept)
        denominator = max(1, lost + added + changed + kept)
        score = (lost + changed) / denominator
        return {
            "older": older,
            "newer": newer,
            "score": round(score, 6),
            "lost_count": lost,
            "added_count": added,
            "changed_count": changed,
            "kept_count": kept,
            "lost_paths": list(diff.lost),
            "changed_paths": list(diff.changed),
            "classification": self.classify_drift(score),
        }

    @staticmethod
    def classify_drift(score: float) -> str:
        if score <= 0.0:
            return "estável"
        if score < 0.20:
            return "benigno"
        if score < 0.50:
            return "preocupante"
        return "crítico"

    def alert_on_threshold(self, report: dict, threshold: float = 0.50) -> bool:
        return float(report.get("score", 0.0)) >= threshold

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("audit", self.NAME, True)
