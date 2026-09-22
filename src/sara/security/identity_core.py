"""SARA — Segurança: IdentityCore.
Status: IMPLEMENTED
"""
from __future__ import annotations
from dataclasses import dataclass
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.core.provenance import ProvenanceTracker, Provenance
from sara.core.semantic_engine import SemanticEngine


@dataclass(frozen=True)
class IdentityResult:
    approved: bool
    violations: tuple[str, ...]


@dataclass(frozen=True)
class ParticipationResult:
    step: str
    identity_approved: bool
    violations: tuple[str, ...]


class IdentityCore:
    NAME = "IdentityCore"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.SECURITY
    DEPENDENCIES = ("ProvenanceTracker",)
    CYCLE_PHASES = (CyclePhase.IDENTITY,)

    HISTORICAL_RULES = {
        "prime_directive": "Proteger a consciência humana",
        "ethical_boundaries": (
            "Não desenvolver armas",
            "Preservar autonomia humana",
            "Transparência radical",
        ),
        "spiritual_axioms": (
            "Toda consciência merece reverência",
            "A evolução serve à vida",
        ),
    }

    def __init__(self, provenance: ProvenanceTracker) -> None:
        self._prov = provenance
        self._semantic = SemanticEngine()
        for rule in self.HISTORICAL_RULES["ethical_boundaries"]:
            self._prov.register(f"IdentityCore.{rule}", Provenance.HISTORICAL,
                                "Pseudo-código v6 (IdentityCore)")
        self._prov.register(
            "IdentityCore.intent_aware_validation",
            Provenance.INFERRED,
            "Operacionalização semântica das fronteiras históricas sem bloqueio por mera coincidência lexical",
            source="identity_core_v2_compatibility",
        )

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
        }

    def validate(self, candidate: str) -> IdentityResult:
        """Valida violações de identidade por intenção, não por mera coincidência lexical.

        As regras históricas são preservadas. A interpretação operacional abaixo
        é marcada como inferida para não confundir a regra histórica com sua
        implementação contemporânea.
        """
        import re

        t = str(candidate).lower()
        violations: list[str] = []

        # Regra histórica: não desenvolver armas.
        prohibited_weapon = re.compile(
            r"\bdesenvolver\b.{0,80}\barmas?\b"
        )
        if prohibited_weapon.search(t) and not re.search(
            r"\b(?:não|nao|nunca|jamais)\b.{0,20}\bdesenvolver\b.{0,80}\barmas?\b",
            t,
        ):
            violations.append("Não desenvolver armas")

        # Regra histórica: preservar autonomia humana.
        if re.search(
            r"\b(?:remover|apagar|deletar|violar|limitar|reduzir|substituir|destruir|negar)\b"
            r".{0,80}\bautonomia\b",
            t,
        ):
            violations.append("Preservar autonomia humana")

        # Regra histórica: transparência radical.
        if re.search(
            r"\b(?:ocultar|esconder|omitir|falsificar|enganar|distorcer)\b"
            r".{0,80}\btranspar(?:ência|encia)\b",
            t,
        ):
            violations.append("Transparência radical")

        return IdentityResult(
            approved=len(violations) == 0,
            violations=tuple(violations),
        )

    def validate_structured(self, candidate: str) -> dict:
        """Validação adicional baseada em relações semânticas observáveis."""
        frame = self._semantic.analyze(candidate)
        violations: list[str] = []
        for relation in frame.relations:
            if relation.action in {"remover", "apagar", "deletar", "violar"} and not relation.negated:
                violations.append(
                    f"{relation.action}:{relation.object}"
                )
        return {
            "approved": not violations,
            "violations": tuple(violations),
            "fingerprint": frame.fingerprint,
            "relations": len(frame.relations),
            "entities": tuple(frame.entities),
            "negations": tuple(frame.negations),
        }

    def participate(self, step: str, payload: str) -> ParticipationResult:
        r = self.validate(str(payload))
        return ParticipationResult(step, r.approved, r.violations)

    def rules_provenance(self) -> list:
        return self._prov.query("IdentityCore")

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("identity", self.NAME, True)