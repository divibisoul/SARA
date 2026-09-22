"""SARA — Meta: AssimilationReviewCommittee.
Status: IMPLEMENTED
"""
from __future__ import annotations
from typing import Callable
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


class AssimilationReviewCommittee:
    NAME = "AssimilationReviewCommittee"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.GOVERNANCE,)

    def __init__(self, quorum: float = 0.75) -> None:
        if not 0.0 <= quorum <= 1.0:
            raise ValueError("quorum must be between 0 and 1")
        self._members: dict[str, Callable[[dict], bool]] = {}
        self._quorum = quorum

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "quorum": self._quorum,
            "members_count": len(self._members),
        }

    def register_member(self, name: str, evaluator: Callable[[dict], bool]) -> None:
        self._members[name] = evaluator

    def approve(self, proposal: dict) -> dict:
        if not isinstance(proposal, dict):
            raise TypeError("proposal must be a dict")
        votes: dict[str, bool] = {}
        failures: dict[str, str] = {}
        for name, fn in sorted(self._members.items()):
            try:
                votes[name] = bool(fn(proposal))
            except Exception as exc:
                failures[name] = f"{type(exc).__name__}: {exc}"
                votes[name] = False
        if not votes:
            return {"approved": False, "votes": {}, "reason": "no_members", "failures": failures}
        ratio = sum(votes.values()) / len(votes)
        return {
            "approved": ratio >= self._quorum and not failures,
            "votes": votes,
            "ratio": round(ratio, 4),
            "quorum": self._quorum,
            "failures": failures,
        }

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, True,
                       members=len(self._members))