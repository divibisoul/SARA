from pathlib import Path

from sara.contracts.base import ModuleStatus
from sara.governance.legal_ai import LegalAI
from sara.meta.transystem_sara import TransystemSARA
from sara.monitoring.decision_trace import DecisionTrace
from sara.monitoring.governance import GovernanceBackend
from sara.research.quantum_crawler import QuantumCrawler
from sara.research.quantum_scanner import QuantumScanner
from sara.security.safe_sandbox import SafeSandbox


class FakeBackend:
    source = "TEST_SOURCE"

    def fetch(self, query):
        return [{"name": "candidate", "license": "MIT"}]


def test_legal_ai_local_chain_is_independently_reported():
    module = LegalAI({"MIT"})
    decision = module.validate_license("test", "MIT")
    assert decision.approved is True
    assert module.verify_chain() is True
    assert module.describe()["local_license_validation_ready"] is True


def test_transystem_does_not_advertise_hardcoded_external_sources():
    module = TransystemSARA()
    assert module.list_sources() == []
    assert module.describe()["external_integration_ready"] is False


def test_quantum_scanner_local_analysis_is_not_blocked_by_optional_tools(tmp_path: Path):
    target = tmp_path / "sample.py"
    target.write_text("def f():\n    return 1\n", encoding="utf-8")
    scanner = QuantumScanner()
    result = scanner.scan(str(target))
    assert scanner.STATUS is ModuleStatus.IMPLEMENTED
    assert result["backend"] == "local_source_parser"
    assert result["syntax_valid"] is True
    assert "f" in result["functions"]


def test_safe_sandbox_static_analysis_has_resource_bounds():
    sandbox = SafeSandbox()
    oversized = sandbox.analyze_static("x = 1\n" * 1_000_001)
    assert oversized.parsed is False
    assert oversized.vulnerabilities[0].startswith("source_too_large:")

    dangerous = sandbox.analyze_static("x.__class__.__subclasses__()")
    assert any("atributo_perigoso" in item for item in dangerous.vulnerabilities)
    assert sandbox.is_isolation_ready() is False


def test_quantum_crawler_reports_only_configured_sources():
    crawler = QuantumCrawler([FakeBackend()])
    assert crawler.list_sources() == ["TEST_SOURCE"]
    candidates = crawler.scan("ai")
    assert len(candidates) == 1
    assert candidates[0].source == "TEST_SOURCE"


def test_asdf_governance_primitives_remain_distinct():
    governance = GovernanceBackend({"SARA": "IMPLEMENTED"})
    trace = DecisionTrace()
    governance.register_decision({"event": "test", "accepted": True})
    trace.log({"event": "test"})
    assert governance.verify_integrity() is True
    assert trace.verify() is True
