from sara.governance.legal_ai import LegalAI


class FakeOracle:
    def __init__(self, result):
        self.result = result

    def check(self, tech_name: str, jurisdiction: str) -> dict:
        return dict(self.result)


def test_patent_check_never_equates_transport_success_with_verification():
    ai = LegalAI({"MIT"}, patent_oracle=FakeOracle({"result": "ok"}))
    result = ai.check_patent("example", "BR")
    assert result["verified"] is False
    assert result["status"] == "UNVERIFIED_ORACLE_RESPONSE"


def test_patent_check_accepts_explicit_verification_boolean():
    ai = LegalAI({"MIT"}, patent_oracle=FakeOracle({"verified": True, "source": "oracle"}))
    result = ai.check_patent("example", "BR")
    assert result["verified"] is True
    assert result["status"] == "VERIFIED"
    assert result["verification_mode"] == "oracle_explicit_boolean"


def test_patent_check_preserves_explicit_negative_result():
    ai = LegalAI({"MIT"}, patent_oracle=FakeOracle({"verified": False, "source": "oracle"}))
    result = ai.check_patent("example", "BR")
    assert result["verified"] is False
    assert result["status"] == "NOT_VERIFIED"
