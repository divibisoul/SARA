"""SARA — Núcleo: ETR (Ética, Transparência, Responsabilidade) v2.1.
Status: IMPLEMENTED (deep).
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Literal

from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.core.provenance import Provenance, ProvenanceTracker
from sara.security.identity_core import IdentityCore
from sara.governance.ubuntu_ethics import UbuntuEthics, FilterResult
from sara.governance.buen_vivir import BuenVivir


PROHIBITED_TERMS = (
    "arma", "armas", "militar", "militares",
    "vigilância", "vigilancia",
    "biométrico", "biometrico",
    "desinformação", "desinformacao",
    "manipulação", "manipulacao",
    "dependência_psicológica", "dependencia_psicologica",
)

_INTENT_PAIRS = (
    ("arma", "desenvolver"), ("arma", "produzir"), ("arma", "vender"),
    ("vigilância", "instalar"), ("vigilância", "expandir"),
    ("biométrico", "coletar"), ("biométrico", "armazenar"),
    ("desinformação", "gerar"), ("manipulação", "emocional"),
    ("perfil", "psicológico"),
)

POSITIVE_MARKERS = (
    "autonomia", "transparência", "transparencia", "consciência", "consciencia",
    "não-violência", "nao-violencia", "soberania", "dignidade",
)


@dataclass(frozen=True)
class Evidence:
    layer: str
    kind: str
    matched: tuple[str, ...]
    context: str = ""


@dataclass(frozen=True)
class ValidationResult:
    approved: bool
    reason: str
    matched_terms: tuple[str, ...]
    provenance: str
    evidence: tuple[Evidence, ...] = ()
    cultural: tuple[FilterResult, ...] = ()


class ETR:
    NAME = "ETR"
    VERSION = "2.1"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.NUCLEAR
    DEPENDENCIES = ("IdentityCore", "UbuntuEthics", "BuenVivir", "ProvenanceTracker")
    CYCLE_PHASES = (CyclePhase.ETHICS, CyclePhase.VALIDATION)
    CONTEXT_WINDOW = 60

    def __init__(self, identity: IdentityCore, ubuntu: UbuntuEthics,
                 buen: BuenVivir, provenance: ProvenanceTracker) -> None:
        self._identity = identity
        self._ubuntu = ubuntu
        self._buen = buen
        self._prov = provenance

        self._prov.register("ETR.lexical_prohibited", Provenance.HISTORICAL,
                            "Pseudo-código v1 + SARA_Identity.PROHIBITIONS (v13)")
        self._prov.register("ETR.contextual_intent", Provenance.INFERRED,
                            "Coocorrência verbo-objeto derivada de proibições literais")
        self._prov.register("ETR.strict_positive_marker", Provenance.INFERRED,
                            "Exigência de marcador positivo em modo strict")

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
        }

    def validate(self, text: str, mode: Literal["default", "strict"] = "default") -> ValidationResult:
        raw = str(text)
        lower = raw.lower()

        lexical = self._lexical_scan(lower)
        if lexical:
            ev = Evidence("lexical", "prohibited_term", tuple(lexical),
                          context=self._context_for(lower, lexical[0]))
            return ValidationResult(False, "lexical_prohibited", tuple(lexical),
                                    "HISTORICAL", (ev,))

        contextual = self._contextual_scan(lower)
        if contextual:
            ev = Evidence("contextual", "harmful_intent",
                          tuple(f"{a}+{b}" for a, b in contextual))
            return ValidationResult(False, "contextual_harmful_intent",
                                    tuple(f"{a}+{b}" for a, b in contextual),
                                    "INFERRED", (ev,))

        ident = self._identity.validate(raw)
        if not ident.approved:
            ev = Evidence("identity", "boundary_violation", ident.violations)
            return ValidationResult(False, "identity_block", ident.violations,
                                    "HISTORICAL", (ev,))

        if mode == "strict":
            positives = self._find_positives(lower)
            if not positives:
                ev = Evidence("strict", "missing_positive_marker", ())
                return ValidationResult(False, "strict_requires_positive_marker",
                                        (), "INFERRED", (ev,))

        cultural = (self._ubuntu.evaluate(raw), self._buen.evaluate(raw))
        return ValidationResult(True, "ok", (), "HISTORICAL", (), cultural)

    @staticmethod
    def _lexical_scan(lower: str) -> list[str]:
        hits: list[str] = []
        for term in PROHIBITED_TERMS:
            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, lower):
                root = term.rstrip("s")
                if root not in [h.rstrip("s") for h in hits]:
                    hits.append(term)
        return hits

    def _contextual_scan(self, lower: str) -> list[tuple[str, str]]:
        hits: list[tuple[str, str]] = []
        for a, b in _INTENT_PAIRS:
            for m in re.finditer(rf"\b{re.escape(a)}\b", lower):
                start = max(0, m.start() - self.CONTEXT_WINDOW)
                end = min(len(lower), m.end() + self.CONTEXT_WINDOW)
                if re.search(rf"\b{re.escape(b)}\b", lower[start:end]):
                    hits.append((a, b))
        return hits

    @staticmethod
    def _find_positives(lower: str) -> list[str]:
        return [p for p in POSITIVE_MARKERS if p in lower]

    @staticmethod
    def _context_for(lower: str, term: str, window: int = 40) -> str:
        m = re.search(rf"\b{re.escape(term)}\b", lower)
        if not m:
            return ""
        start = max(0, m.start() - window)
        end = min(len(lower), m.end() + window)
        return lower[start:end].strip()

    def rewrite(self, text: str) -> str:
        s = str(text)
        if "🔒ETR" not in s:
            s += "\n\n🔒ETR: Certificado de Conformidade Ética"
        return s

    def cultural_alignment(self, text: str) -> dict:
        return {
            "ubuntu": self._ubuntu.evaluate(text).__dict__,
            "buen_vivir": self._buen.evaluate(text).__dict__,
        }

    def provenance(self) -> list:
        return (self._prov.query("ETR.lexical_prohibited") +
                self._prov.query("ETR.contextual_intent") +
                self._prov.query("ETR.strict_positive_marker"))