"""SARA — Meta: ERU recovery advisor.
Status: IMPLEMENTED — candidatos a recuperação; nenhuma reintegração automática.
"""
from __future__ import annotations

from sara.meta.eru_engine import ERU_Engine
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


class ERURecoveryAdvisor:
    NAME = "ERURecoveryAdvisor"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = ("ERU_Engine",)
    CYCLE_PHASES = (CyclePhase.PERSISTENCE,)

    _WEIGHTS = {
        "function": 1.00,
        "method": 1.00,
        "rule": 0.95,
        "class": 0.90,
        "dependency": 0.90,
        "security": 0.90,
        "memory": 0.85,
        "state": 0.80,
        "config": 0.60,
        "other": 0.50,
    }

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

    def find_lost_capabilities(self, older: str, newer: str) -> list[dict]:
        diff = self._eru.compare(older, newer)
        candidates: list[dict] = []
        for path in diff.lost:
            if path == "__missing_snapshot__":
                continue
            kind = self._infer_kind(path)
            candidates.append({
                "path": path,
                "kind": kind,
                "impact": self._WEIGHTS.get(kind, self._WEIGHTS["other"]),
                "source_snapshot": older,
                "target_snapshot": newer,
                "provenance": "ERU_STRUCTURAL_CANDIDATE",
                "automatic_reintegration": False,
            })
        return candidates

    def rank_by_impact(self, candidates: list[dict]) -> list[dict]:
        return sorted(
            (dict(c) for c in candidates),
            key=lambda item: (-float(item["impact"]), item["path"]),
        )

    def propose_reintegration(self, older: str, newer: str) -> dict:
        candidates = self.rank_by_impact(
            self.find_lost_capabilities(older, newer)
        )
        recovery = self._eru.recover(older, newer)
        return {
            "older": older,
            "newer": newer,
            "candidates": candidates,
            "recovered_paths_preview": list(recovery.get("recovered_paths", [])),
            "state_fused": recovery.get("state_fused"),
            "approval_required": True,
            "provenance": "ERU_STRUCTURAL_RECONCILIATION",
        }

    @staticmethod
    def _infer_kind(path: str) -> str:
        lower = str(path).lower()
        for token, kind in (
            ("function", "function"),
            ("method", "method"),
            ("rule", "rule"),
            ("class", "class"),
            ("depend", "dependency"),
            ("security", "security"),
            ("memory", "memory"),
            ("state", "state"),
            ("config", "config"),
        ):
            if token in lower:
                return kind
        return "other"

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("audit", self.NAME, True)
