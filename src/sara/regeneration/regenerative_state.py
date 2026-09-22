"""SARA — explicit state machine for regenerative cycles."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from sara.contracts.base import CyclePhase


class CycleState(str, Enum):
    CREATED = "CREATED"
    PREFLIGHT = "PREFLIGHT"
    RUNNING = "RUNNING"
    REGENERATING = "REGENERATING"
    VALIDATING = "VALIDATING"
    CONVERGED = "CONVERGED"
    ROLLED_BACK = "ROLLED_BACK"
    ABORTED = "ABORTED"
    COMPLETED = "COMPLETED"


@dataclass
class StateTransition:
    previous: str
    current: str
    reason: str
    ts: str


@dataclass
class RegenerativeState:
    cycle_id: str
    state: CycleState = CycleState.CREATED
    phase: CyclePhase | None = None
    iteration: int = 0
    transitions: list[StateTransition] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def transition(self, new_state: CycleState, reason: str, ts: str) -> None:
        previous = self.state.value
        self.state = new_state
        self.transitions.append(StateTransition(previous, new_state.value, reason, ts))

    def set_phase(self, phase: CyclePhase) -> None:
        self.phase = phase

    def converged(self) -> bool:
        return self.state == CycleState.CONVERGED
