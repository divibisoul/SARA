"""L7 ASASF adapter over SARA governance and audit authorities.

No synthetic remediation is performed here. Stages are executed only by an
injected executor, and verification is explicitly attributed to that executor
unless an independent verifier exists elsewhere in the stack.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal
from uuid import uuid4

from sara.monitoring.decision_trace import DecisionTrace
from sara.monitoring.governance import GovernanceBackend


StageExecutor = Callable[[str, str], bool | dict[str, Any]]
VerificationStatus = Literal["not_observed", "executor_confirmed"]


@dataclass(frozen=True)
class RemediationState:
    id: str
    issue: str
    stage: str
    status: str
    verification: VerificationStatus = "not_observed"
    evidence: Any = None


class ASASFPanelModule:
    NAME = "ASASFPanelModule"

    def __init__(
        self,
        governance: GovernanceBackend | None = None,
        trace: DecisionTrace | None = None,
        executor: StageExecutor | None = None,
    ) -> None:
        self._governance = governance
        self._trace = trace
        self._executor = executor
        self._state: RemediationState | None = None

    def bind(
        self,
        governance: GovernanceBackend,
        trace: DecisionTrace,
        executor: StageExecutor,
    ) -> None:
        self._governance = governance
        self._trace = trace
        self._executor = executor

    @staticmethod
    def _normalize_stage_result(result: bool | dict[str, Any]) -> tuple[bool, Any]:
        if isinstance(result, bool):
            return result, None
        if isinstance(result, dict) and "ok" in result:
            return bool(result["ok"]), result.get("evidence")
        raise TypeError("ASASF_STAGE_RESULT_INVALID")

    def start(self, issue: str, severity: str) -> RemediationState:
        if not issue.strip():
            raise ValueError("ISSUE_REQUIRED")
        if self._executor is None or self._governance is None or self._trace is None:
            raise RuntimeError("ASASF_UNBOUND")

        remediation_id = "remediation-" + uuid4().hex
        request = {
            "type": "asasf.remediation.requested",
            "id": remediation_id,
            "issue": issue,
            "severity": severity,
        }
        self._governance.register_decision(request)
        self._trace.log(request)

        for stage in ("detect", "isolate", "repair", "verify"):
            try:
                ok, evidence = self._normalize_stage_result(
                    self._executor(remediation_id, stage)
                )
            except Exception as exc:
                failure = {
                    "type": "asasf.remediation.stage_failed",
                    "id": remediation_id,
                    "stage": stage,
                    "error": str(exc),
                }
                self._governance.register_decision(failure)
                self._trace.log(failure)
                self._state = RemediationState(
                    remediation_id,
                    issue,
                    stage,
                    "failed",
                    evidence={"error": str(exc)},
                )
                return self._state

            stage_event = {
                "type": "asasf.remediation.stage",
                "id": remediation_id,
                "stage": stage,
                "ok": ok,
                "evidence": evidence,
            }
            self._governance.register_decision(stage_event)
            self._trace.log(stage_event)

            if not ok:
                self._state = RemediationState(
                    remediation_id,
                    issue,
                    stage,
                    "failed",
                    evidence=evidence,
                )
                return self._state

            if stage == "verify":
                self._state = RemediationState(
                    remediation_id,
                    issue,
                    stage,
                    "completed",
                    verification="executor_confirmed",
                    evidence=evidence,
                )
            else:
                self._state = RemediationState(
                    remediation_id,
                    issue,
                    stage,
                    "running",
                    evidence=evidence,
                )

        return self._state

    def get_state(self) -> RemediationState | None:
        return self._state


asasfPanelModule = ASASFPanelModule()
