"""Regressões de contratos públicos do pacote SARA."""

from dataclasses import fields

from sara.governance import GovernedSARA, AssimilationReport


def test_governance_exports_preserve_assimilation_report_contract():
    assert GovernedSARA.__name__ == "GovernedSARA"
    assert AssimilationReport.__name__ == "AssimilationReport"
    assert {f.name for f in fields(AssimilationReport)} == {
        "system", "component", "accepted", "notes"
    }
