"""L7 ASASF adapter over SARA governance and audit authorities.

No synthetic remediation is performed here. Stages are executed only by an
injected executor; this module never fabricates coherence or system status.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from sara.monitoring.decision_trace import DecisionTrace
from sara.monitoring.governance import GovernanceBackend

StageExecutor = Callable[[str, str], bool]

@dataclass(frozen=True)
class RemediationState:
    id: str
    issue: str
    stage: str
    status: str

class ASASFPanelModule:
    NAME = "ASASFPanelModule"

    def __init__(self, governance: GovernanceBackend | None = None, trace: DecisionTrace | None = None, executor: StageExecutor | None = None) -> None:
        self._governance = governance
        self._trace = trace
        self._executor = executor
        self._state: Optional[RemediationState] = None

    def bind(self, governance: GovernanceBackend, trace: DecisionTrace, executor: StageExecutor) -> None:
        self._governance, self._trace, self._executor = governance, trace, executor

    def start(self, issue: str, severity: str) -> RemediationState:
        if not issue.strip():
            raise ValueError("ISSUE_REQUIRED")
        if self._executor is None or self._governance is None or self._trace is None:
            raise RuntimeError("ASASF_UNBOUND")
        remediation_id = "remediation-" + str(self._trace.next_sequence())
        for stage in ("detect", "isolate", "repair", "verify"):
            if not self._executor(remediation_id, stage):
                self._state = RemediationState(remediation_id, issue, stage, "failed")
                return self._state
            self._state = RemediationState(remediation_id, issue, stage, "running")
        self._state = RemediationState(remediation_id, issue, "verify", "completed")
        return self._state

    def get_state(self) -> Optional[RemediationState]:
        return self._state

asasfPanelModule = ASASFPanelModule()
