"""SARA — Governança: UbuntuEthics.
Status: IMPLEMENTED
"""
from __future__ import annotations
from dataclasses import dataclass
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


@dataclass(frozen=True)
class FilterResult:
    filter_name: str
    aligned: bool
    keywords_matched: tuple[str, ...]
    provenance: str = "ESPECIFICAÇÃO_HISTÓRICA_v5"


class UbuntuEthics:
    NAME = "UbuntuEthics"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.GOVERNANCE
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.VALIDATION,)

    PRINCIPLES = (
        "Eu sou porque nós somos",
        "Respeito à coletividade",
        "Cuidado com as gerações futuras",
    )
    KEYWORDS = ("coletivo", "comunidade", "nós", "gerações", "futuro")

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "principles_count": len(self.PRINCIPLES),
        }

    def evaluate(self, text: str) -> FilterResult:
        t = str(text).lower()
        hits = tuple(k for k in self.KEYWORDS if k in t)
        return FilterResult(
            filter_name="UbuntuEthics",
            aligned=len(hits) > 0,
            keywords_matched=hits,
        )

    def evaluate_structured(self, text: str) -> dict:
        """Avaliação adicional por relações semânticas e evidência contextual."""
        from sara.core.semantic_engine import SemanticEngine
        frame = SemanticEngine.analyze(text)
        lower = str(text).lower()
        evidence: list[str] = []
        for relation in frame.relations:
            if relation.object in {"comunidade", "coletivo", "nós", "gerações", "futuro"}:
                evidence.append(
                    f"{relation.action}:{relation.object}:clause={relation.clause_index}"
                )
        keyword_hits = [k for k in self.KEYWORDS if k in lower]
        score = min((len(keyword_hits) + len(evidence)) / 4.0, 1.0)
        return {
            "filter_name": self.NAME,
            "score": round(score, 4),
            "aligned": score >= 0.25,
            "keyword_hits": keyword_hits,
            "semantic_evidence": evidence,
            "fingerprint": frame.fingerprint,
        }

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("validation", self.NAME, True,
                       principles=len(self.PRINCIPLES))