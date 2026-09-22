"""SARA — Pesquisa: InnovationRadar v2.
Status: IMPLEMENTED (deep).
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from sara.core.etr import ETR
from sara.core.itr import ITR
from sara.security.identity_core import IdentityCore
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


@dataclass
class Score:
    relevance: float
    innovation: float
    ethics: float
    strategic: float
    risk: float
    total: float

    def as_dict(self) -> dict:
        return asdict(self)


class InnovationRadar:
    NAME = "InnovationRadar"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.RESEARCH
    DEPENDENCIES = ("ETR", "ITR", "IdentityCore")
    CYCLE_PHASES = (CyclePhase.GOVERNANCE,)

    WEIGHTS = {"relevance": 0.25, "innovation": 0.20, "ethics": 0.25,
               "strategic": 0.20, "risk": 0.10}

    def __init__(self, etr: ETR, itr: ITR, identity: IdentityCore) -> None:
        self._etr = etr
        self._itr = itr
        self._identity = identity
        self._thresholds = {"default": 0.55}

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "threshold_default": self._thresholds.get("default"),
        }

    def threshold(self, category: str = "default") -> float:
        return self._thresholds.get(category, 0.55)

    def score(self, candidate: dict) -> Score:
        description = str(candidate.get("description", ""))
        name = str(candidate.get("name", ""))

        relevance = min(len(description) / 400.0, 1.0)
        innovation_kw = ("novo", "inov", "breakthrough", "sota", "first")
        innovation = min(sum(1 for k in innovation_kw if k in description.lower()) / 3.0, 1.0)

        etr_res = self._etr.validate(description)
        ethics = 1.0 if etr_res.approved else 0.0

        identity_res = self._identity.validate(f"{name} {description}")
        strategic = 1.0 if identity_res.approved else 0.0

        risk = 0.0
        banned_licenses = ("GPL", "AGPL", "Proprietary-EULA")
        if any(lic in candidate.get("license", "") for lic in banned_licenses):
            risk += 0.5
        if any(dep in ("gov_api", "surveillance_sdk") for dep in candidate.get("dependencies", [])):
            risk += 0.5
        risk = min(risk, 1.0)

        total = (
            self.WEIGHTS["relevance"] * relevance
            + self.WEIGHTS["innovation"] * innovation
            + self.WEIGHTS["ethics"] * ethics
            + self.WEIGHTS["strategic"] * strategic
            + self.WEIGHTS["risk"] * (1.0 - risk)
        )
        return Score(relevance, innovation, ethics, strategic, risk, total)

    def filter(self, candidates: list[dict],
               category: str = "default") -> list[tuple[dict, Score]]:
        threshold = self.threshold(category)
        out: list[tuple[dict, Score]] = []
        for c in candidates:
            s = self.score(c)
            if s.total >= threshold:
                out.append((c, s))
        out.sort(key=lambda x: x[1].total, reverse=True)
        return out

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, True,
                       threshold=self._thresholds.get("default"))