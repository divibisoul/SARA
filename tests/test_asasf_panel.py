from sara.meta.ASASFPanelModule import ASASFPanelModule
from sara.monitoring.decision_trace import DecisionTrace
from sara.monitoring.governance import GovernanceBackend


def test_asasf_records_all_stages_and_attributes_verification():
    governance = GovernanceBackend({"SARA": "IMPLEMENTED"})
    trace = DecisionTrace()
    calls = []

    def executor(remediation_id, stage):
        calls.append((remediation_id, stage))
        return {"ok": True, "evidence": {"stage": stage}}

    module = ASASFPanelModule(governance, trace, executor)
    state = module.start("test issue", "warning")

    assert state.status == "completed"
    assert state.stage == "verify"
    assert state.verification == "executor_confirmed"
    assert state.evidence == {"stage": "verify"}
    assert [stage for _, stage in calls] == ["detect", "isolate", "repair", "verify"]
    assert trace.verify() is True
    assert governance.verify_integrity() is True
