from sara.meta.aeternum_enforcement_pipeline import AeternumEnforcementPipelineModule
from sara.monitoring.decision_trace import DecisionTrace
from sara.monitoring.governance import GovernanceBackend


class GovernanceDenied:
    def assimilate(self, proposal, ctx=None):
        return type("Decision", (), {"accepted": False, "reasons": ["denied"]})()


class GovernanceAccepted:
    def assimilate(self, proposal, ctx=None):
        return type("Decision", (), {"accepted": True, "reasons": []})()


def test_enforcement_denied_does_not_claim_execution():
    governance = GovernanceBackend({"SARA": "IMPLEMENTED"})
    trace = DecisionTrace()
    module = AeternumEnforcementPipelineModule(
        GovernanceDenied(),
        governance,
        trace,
        executor=lambda action, params: {"done": True},
    )
    result = module.execute("change", {}, {"name": "test"})
    assert result.status == "denied"
    assert result.execution == "not_claimed"


def test_enforcement_requires_verifier_for_completed_status():
    governance = GovernanceBackend({"SARA": "IMPLEMENTED"})
    trace = DecisionTrace()
    module = AeternumEnforcementPipelineModule(
        GovernanceAccepted(),
        governance,
        trace,
        executor=lambda action, params: {"done": True},
    )
    result = module.execute("change", {}, {"name": "test"})
    assert result.status == "executed_unverified"
    assert result.execution == "real"
    assert result.detail["verification"] == "not_bound"


def test_enforcement_completed_requires_positive_verifier():
    governance = GovernanceBackend({"SARA": "IMPLEMENTED"})
    trace = DecisionTrace()
    module = AeternumEnforcementPipelineModule(
        GovernanceAccepted(),
        governance,
        trace,
        executor=lambda action, params: {"done": True},
        verifier=lambda action, execution: execution["done"],
    )
    result = module.execute("change", {}, {"name": "test"})
    assert result.status == "completed"
    assert result.execution == "real"
    assert result.detail["verification"] == "verified"
