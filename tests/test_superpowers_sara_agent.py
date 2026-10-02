from sara.integrations.superpowers_sara_agent import SuperpowersSaraAgent


def test_superpowers_agent_binds_requested_sara_targets():
    agent = SuperpowersSaraAgent()
    agent.bind(ara=object(), etr=object(), itr=object(), rgo=object(), mmd=object())
    state = agent.describe()
    assert state["status"] == "BOUND"
    assert state["bound_targets"] == ["ARA", "ETR", "ITR", "MMD", "RGO"]


def test_superpowers_agent_requires_evidence():
    agent = SuperpowersSaraAgent()
    agent.bind(ara=object(), etr=object(), itr=object(), rgo=object(), mmd=object())
    try:
        agent.prepare("ARA", "audit", evidence={})
    except ValueError as exc:
        assert str(exc) == "SUPERPOWERS_SARA_EVIDENCE_REQUIRED"
    else:
        raise AssertionError("expected evidence gate")
