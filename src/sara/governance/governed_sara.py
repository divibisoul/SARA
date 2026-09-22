"""SARA — Governança: GovernedSARA v2.
Status: IMPLEMENTED (deep).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from sara.meta.assimilation_committee import AssimilationReviewCommittee
from sara.governance.legal_compliance import LegalCompliance
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


@dataclass
class GovernanceDecision:
    accepted: bool
    committee: dict
    compliance: dict
    radar: dict
    reasons: list[str] = field(default_factory=list)


class GovernedSARA:
    NAME = "GovernedSARA"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.GOVERNANCE
    DEPENDENCIES = ("AssimilationReviewCommittee", "LegalCompliance", "InnovationRadar")
    CYCLE_PHASES = (CyclePhase.GOVERNANCE,)

    def __init__(self, committee: AssimilationReviewCommittee,
                 compliance: LegalCompliance, radar=None) -> None:
        self._committee = committee
        self._compliance = compliance
        self._radar = radar

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "radar_attached": self._radar is not None,
        }

    def assimilate(self, proposal: dict, ctx=None) -> GovernanceDecision:
        reasons: list[str] = []

        committee = self._committee.approve(proposal)
        if not committee["approved"]:
            reasons.append("committee_rejected")

        compliance = self._compliance.validate(
            proposal.get("license", ""),
            context=proposal.get("compliance_context"),
        )
        if not compliance.approved:
            reasons.append("compliance_rejected")

        radar_out: dict = {}
        if self._radar is not None:
            score = self._radar.score(proposal)
            radar_out = score.as_dict()
            if score.total < self._radar.threshold():
                reasons.append("radar_below_threshold")

        accepted = len(reasons) == 0

        if ctx is not None and hasattr(ctx, "emit_decision"):
            ctx.emit_decision({
                "event": "governance_decision",
                "accepted": accepted,
                "reasons": reasons,
                "proposal_name": proposal.get("name", "unknown"),
            })

        return GovernanceDecision(
            accepted=accepted,
            committee=committee,
            compliance=compliance.__dict__,
            radar=radar_out,
            reasons=reasons,
        )

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, True)