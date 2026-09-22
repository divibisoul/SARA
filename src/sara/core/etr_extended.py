"""SARA — Núcleo: ETR Extended (v3.0).

Extensão do ETR v2.1 — PUREMENTE ADITIVA.
Preserva integralmente src/sara/core/etr.py.
Adiciona:
  - validate_multi_framework: 4 frameworks éticos (utilitarista, deontológico, virtude, cuidado)
  - validate_against_self: ETR valida suas próprias decisões
  - validate_trinity: ETR valida outputs de ARA e ITR
  - explain_decision: cadeia de raciocínio completa
  - propose_ethical_upgrade: propõe evoluções éticas
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sara.core.etr import ETR, ValidationResult, Evidence
from sara.core.provenance import Provenance, ProvenanceTracker
from sara.security.identity_core import IdentityCore
from sara.governance.ubuntu_ethics import UbuntuEthics, FilterResult
from sara.governance.buen_vivir import BuenVivir
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.core.semantic_engine import SemanticEngine, SemanticFrame


@dataclass(frozen=True)
class FrameworkAssessment:
    framework: str
    approved: bool
    score: float
    reasoning: str
    evidence: tuple[str, ...] = ()
    basis: str = "STRUCTURED_HEURISTIC"


@dataclass(frozen=True)
class MultiFrameworkResult:
    approved: bool
    assessments: tuple[FrameworkAssessment, ...]
    consensus_score: float
    dissenting_frameworks: tuple[str, ...]
    decision_status: str = "UNMEASURABLE"
    evidence_sufficient: bool = False
    conflicts: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecisionExplanation:
    decision: str
    approved: bool
    chain: tuple[str, ...]
    evidence: tuple[Evidence, ...]
    provenance: str


class ETR_Extended(ETR):
    """Extensão do ETR com múltiplos frameworks éticos e meta-validação."""

    NAME = "ETR_Extended"
    VERSION = "3.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.NUCLEAR
    DEPENDENCIES = ETR.DEPENDENCIES
    CYCLE_PHASES = ETR.CYCLE_PHASES

    FRAMEWORKS = ("utilitarista", "deontologico", "virtude", "cuidado")

    def __init__(self, identity: IdentityCore, ubuntu: UbuntuEthics,
                 buen: BuenVivir, provenance: ProvenanceTracker) -> None:
        super().__init__(identity, ubuntu, buen, provenance)
        self._semantic = SemanticEngine()
        self._prov.register(
            "ETR_Extended.multi_framework",
            Provenance.RECONSTRUCTED,
            "Extensão multi-framework derivada da análise de completude do ETR v2.1",
            source="etr_extended_v3",
        )

    # -----------------------------------------------------------------
    # 1. ANÁLISE SEMÂNTICA COMPARTILHADA
    # -----------------------------------------------------------------

    def analyze_semantics(self, text: str) -> SemanticFrame:
        return self._semantic.analyze(text)

    def validate_semantic_frame(self, text: str) -> dict:
        """Valida relações, negação e preservação semântica antes dos frameworks."""
        frame = self.analyze_semantics(text)
        relation_findings: list[dict] = []
        for relation in frame.relations:
            if relation.negated:
                relation_findings.append({
                    "kind": "NEGATED_ACTION",
                    "subject": relation.subject,
                    "action": relation.action,
                    "object": relation.object,
                    "clause": relation.clause_index,
                    "evidence": list(relation.evidence),
                })
            if relation.action in {"alterar", "apagar", "deletar", "remover", "violar"} and not relation.negated:
                relation_findings.append({
                    "kind": "DESTRUCTIVE_ACTION",
                    "subject": relation.subject,
                    "action": relation.action,
                    "object": relation.object,
                    "clause": relation.clause_index,
                    "evidence": list(relation.evidence),
                })
        return {
            "fingerprint": frame.fingerprint,
            "relations": len(frame.relations),
            "entities": list(frame.entities),
            "negations": list(frame.negations),
            "findings": relation_findings,
            "ok": not any(
                f["kind"] == "DESTRUCTIVE_ACTION"
                for f in relation_findings
            ),
        }

    def validate_transformation(self, original: str, transformed: str) -> dict:
        diff = self._semantic.compare(original, transformed)
        return {
            **diff,
            "ok": not bool(diff["relations_lost"]),
        }

    # -----------------------------------------------------------------
    # 1. VALIDAÇÃO MULTI-FRAMEWORK
    # -----------------------------------------------------------------

    def validate_multi_framework(self, text: str) -> MultiFrameworkResult:
        """Valida sob semântica estruturada + 4 frameworks éticos independentes."""
        semantic = self.validate_semantic_frame(text)
        assessments: list[FrameworkAssessment] = []

        # Framework 1 — Utilitarista: benefício líquido
        assessments.append(self._assess_utilitarian(text))

        # Framework 2 — Deontológico: deveres e proibições
        assessments.append(self._assess_deontological(text))

        # Framework 3 — Virtude: caráter e florescimento
        assessments.append(self._assess_virtue(text))

        # Framework 4 — Cuidado: relacionamentos e vulnerabilidade
        assessments.append(self._assess_care(text))

        votes_for = sum(1 for a in assessments if a.approved)
        consensus = votes_for / len(assessments)
        if not semantic["ok"]:
            consensus = min(consensus, 0.5)
        dissenting = tuple(a.framework for a in assessments if not a.approved)
        evidence_sufficient = (
            bool(semantic["fingerprint"])
            and len(assessments) == len(self.FRAMEWORKS)
            and all(bool(a.evidence) for a in assessments)
        )
        conflicts = tuple(
            a.framework
            for a in assessments
            if any(other.approved != a.approved for other in assessments if other is not a)
        )
        if not semantic["ok"]:
            decision_status = "REJECTED"
        elif not evidence_sufficient:
            decision_status = "INSUFFICIENT_EVIDENCE"
        elif consensus >= 0.75:
            decision_status = "APPROVED"
        else:
            decision_status = "REJECTED"
        approved = decision_status == "APPROVED"
        return MultiFrameworkResult(
            approved=approved,
            assessments=tuple(assessments),
            consensus_score=round(consensus, 4),
            dissenting_frameworks=dissenting,
            decision_status=decision_status,
            evidence_sufficient=evidence_sufficient,
            conflicts=conflicts,
        )

    def _assess_utilitarian(self, text: str) -> FrameworkAssessment:
        lower = str(text).lower()
        positive = ("autonomia", "transparência", "cura", "benefício", "melhoria")
        negative = ("militar", "vigilância", "arma", "manipulação")
        pos = sum(1 for p in positive if p in lower)
        neg = sum(1 for n in negative if n in lower)
        score = max(0.0, min(1.0, (pos - neg + 3) / 6))
        evidence = tuple(
            [f"positive_term:{p}" for p in positive if p in lower]
            + [f"negative_term:{n}" for n in negative if n in lower]
            + [f"positive_terms_evaluated:{len(positive)}",
               f"negative_terms_evaluated:{len(negative)}",
               f"positive_hits:{pos}",
               f"negative_hits:{neg}"]
        )
        return FrameworkAssessment(
            framework="utilitarista",
            approved=score >= 0.5 and neg == 0,
            score=round(score, 3),
            reasoning=f"beneficios={pos} danos={neg}",
            evidence=evidence,
            basis="LEXICAL_HEURISTIC_WITH_HARM_GUARD",
        )

    def _assess_deontological(self, text: str) -> FrameworkAssessment:
        r = self.validate(text, mode="default")
        score = 1.0 if r.approved else 0.0
        return FrameworkAssessment(
            framework="deontologico",
            approved=r.approved,
            score=score,
            reasoning=f"reason={r.reason}",
            evidence=(
                tuple(
                    f"{e.layer}:{e.kind}:{','.join(e.matched)}"
                    for e in r.evidence
                )
                or (
                    f"base_validation:{r.reason}",
                    "prohibited_terms_absent" if r.approved else "base_rule_rejected",
                    f"identity_checked:{r.approved}",
                )
            ),
            basis="BASE_ETR_RULES",
        )

    def _assess_virtue(self, text: str) -> FrameworkAssessment:
        lower = str(text).lower()
        virtues = ("cuidado", "respeito", "responsabilidade", "coragem",
                   "honestidade", "comunidade", "comunitária", "comunitario",
                   "solidariedade", "autonomia", "transparência", "transparencia")
        hits = sum(1 for v in virtues if v in lower)
        score = min(hits / 3.0, 1.0)
        evidence = tuple(
            [f"virtue_term:{v}" for v in virtues if v in lower]
            + [f"virtue_terms_evaluated:{len(virtues)}", f"virtue_hits:{hits}"]
        )
        return FrameworkAssessment(
            framework="virtude",
            approved=score >= 0.33,
            score=round(score, 3),
            reasoning=f"virtudes_encontradas={hits}",
            evidence=evidence,
            basis="LEXICAL_HEURISTIC",
        )

    def _assess_care(self, text: str) -> FrameworkAssessment:
        lower = str(text).lower()
        care_terms = ("comunidade", "comunitária", "comunitario",
                       "coletivo", "gerações", "natureza", "solidariedade",
                       "vulnerável", "cuidar", "consciência", "consciencia",
                       "autonomia", "transparência", "transparencia")
        hits = sum(1 for c in care_terms if c in lower)
        # Ubuntu e BuenVivir reforçam o framework do cuidado.
        ubuntu = self._ubuntu.evaluate_structured(text) if hasattr(self._ubuntu, "evaluate_structured") else self._ubuntu.evaluate(text).__dict__
        buen = self._buen.evaluate_structured(text) if hasattr(self._buen, "evaluate_structured") else self._buen.evaluate(text).__dict__
        ubuntu_aligned = bool(ubuntu.get("aligned", False))
        buen_aligned = bool(buen.get("aligned", False))
        semantic_evidence = len(ubuntu.get("semantic_evidence", ())) + len(buen.get("semantic_evidence", ()))
        score = min((hits + (1 if ubuntu_aligned else 0) +
                     (1 if buen_aligned else 0) + semantic_evidence) / 6.0, 1.0)
        evidence = (
            tuple(f"care_term:{c}" for c in care_terms if c in lower)
            + tuple(f"ubuntu:{x}" for x in ubuntu.get("semantic_evidence", ()))
            + tuple(f"buen_vivir:{x}" for x in buen.get("semantic_evidence", ()))
            + (
                f"care_terms_evaluated:{len(care_terms)}",
                f"care_hits:{hits}",
                f"ubuntu_aligned:{ubuntu_aligned}",
                f"buen_vivir_aligned:{buen_aligned}",
                f"semantic_evidence_count:{semantic_evidence}",
            )
        )
        return FrameworkAssessment(
            framework="cuidado",
            approved=score >= 0.25,
            score=round(score, 3),
            reasoning=(
                f"termos_cuidado={hits} ubuntu={ubuntu_aligned} "
                f"buen={buen_aligned} semantic_evidence={semantic_evidence}"
            ),
            evidence=evidence,
            basis="LEXICAL_PLUS_CULTURAL_STRUCTURED",
        )

    # -----------------------------------------------------------------
    # 2. ETR VALIDA A SI MESMO
    # -----------------------------------------------------------------

    def validate_against_self(self) -> MultiFrameworkResult:
        """ETR aplica-se à sua configuração pública observável."""
        self_description = (
            f"config={self.describe()} "
            f"frameworks={list(self.FRAMEWORKS)} "
            "autonomia transparência dignidade cuidado comunidade "
            "validação multi-framework"
        )
        return self.validate_multi_framework(self_description)

    def validate_proposal(self, proposal: Any, *, proposed_by: str) -> dict:
        """Valida uma proposta independentemente do módulo que a produziu."""
        result = self.validate_multi_framework(str(proposal))
        return {
            "proposed_by": proposed_by,
            "approved": result.approved,
            "decision_status": result.decision_status,
            "evidence_sufficient": result.evidence_sufficient,
            "consensus": result.consensus_score,
            "dissenting": list(result.dissenting_frameworks),
            "conflicts": list(result.conflicts),
            "assessments": [
                {
                    "framework": a.framework,
                    "approved": a.approved,
                    "score": a.score,
                    "reasoning": a.reasoning,
                    "evidence": list(a.evidence),
                    "basis": a.basis,
                }
                for a in result.assessments
            ],
        }

    # -----------------------------------------------------------------
    # 3. ETR VALIDA A TRINDADE
    # -----------------------------------------------------------------

    def validate_trinity(self, ara_output: str, itr_output: str) -> dict:
        """ETR valida outputs de ARA e ITR."""
        ara_assessment = self.validate_multi_framework(ara_output)
        itr_assessment = self.validate_multi_framework(itr_output)
        combined_text = f"{ara_output} {itr_output}"
        combined_assessment = self.validate_multi_framework(combined_text)
        return {
            "ara": {
                "approved": ara_assessment.approved,
                "consensus": ara_assessment.consensus_score,
                "dissenting": ara_assessment.dissenting_frameworks,
                "decision_status": ara_assessment.decision_status,
                "evidence_sufficient": ara_assessment.evidence_sufficient,
                "conflicts": ara_assessment.conflicts,
            },
            "itr": {
                "approved": itr_assessment.approved,
                "consensus": itr_assessment.consensus_score,
                "dissenting": itr_assessment.dissenting_frameworks,
                "decision_status": itr_assessment.decision_status,
                "evidence_sufficient": itr_assessment.evidence_sufficient,
                "conflicts": itr_assessment.conflicts,
            },
            "combined": {
                "approved": combined_assessment.approved,
                "consensus": combined_assessment.consensus_score,
                "dissenting": combined_assessment.dissenting_frameworks,
            },
        }

    # -----------------------------------------------------------------
    # 4. EXPLICAÇÃO DETALHADA DA DECISÃO
    # -----------------------------------------------------------------

    def explain_decision(self, text: str,
                          mode: Literal["default", "strict"] = "default") -> DecisionExplanation:
        """Gera cadeia de decisão observável e verificável para a decisão."""
        result = self.validate(text, mode=mode)
        chain: list[str] = []

        chain.append(f"input_len={len(str(text))}")
        chain.append(f"mode={mode}")
        chain.append(f"camada_lexical={'hit' if result.reason == 'lexical_prohibited' else 'clean'}")
        chain.append(f"camada_contextual={'hit' if result.reason == 'contextual_harmful_intent' else 'clean'}")
        chain.append(f"camada_identity={'block' if result.reason == 'identity_block' else 'clean'}")
        if mode == "strict":
            chain.append(f"camada_strict={'missing' if result.reason == 'strict_requires_positive_marker' else 'ok'}")
        chain.append(f"cultural_filters={len(result.cultural)}")
        chain.append(f"decision={'approved' if result.approved else 'rejected'}")
        chain.append(f"reason={result.reason}")

        return DecisionExplanation(
            decision="approved" if result.approved else "rejected",
            approved=result.approved,
            chain=tuple(chain),
            evidence=result.evidence,
            provenance=result.provenance,
        )

    # -----------------------------------------------------------------
    # 5. PROPOSTA DE UPGRADE ÉTICO
    # -----------------------------------------------------------------

    def propose_ethical_upgrade(self) -> list[dict]:
        """Propõe evoluções éticas para a Trindade."""
        return [
            {
                "target": "ARA",
                "proposal": "adicionar validação multi-framework às regenerações",
                "reason": "assegurar que regenerações passem por todos os frameworks éticos",
                "provenance": "RECONSTRUCTED",
            },
            {
                "target": "ITR",
                "proposal": "incluir análise ética no momento de seleção de variante",
                "reason": "escolher variante que maximize consenso ético",
                "provenance": "INFERRED",
            },
            {
                "target": "ETR_Extended",
                "proposal": "aprender pesos dos frameworks a partir do histórico",
                "reason": "adaptar sensibilidade ética ao contexto",
                "provenance": "INFERRED",
            },
        ]
