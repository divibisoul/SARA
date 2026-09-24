"""SARA — Núcleo: ITR Extended (v3.0).

Extensão do ITR v2.1 — PUREMENTE ADITIVA.
Preserva integralmente src/sara/core/itr.py.
Adiciona:
  - generate_strategic: plano estratégico multi-fase
  - execute_composed: pipelines compostos com pontos de rollback
  - analyze_patterns: reconhecimento de padrões nos objetivos
  - optimize_registry: ITR melhora seu próprio registro de passos
  - propose_trinity_evolution: ITR propõe evoluções para toda a Trindade
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from sara.core.itr import (
    ITR, Strategy, ExecutionResult,
    _STEP_REGISTRY, _normalize, _extract_keywords,
    _structure_objective, _add_guardrails,
)
from sara.core.provenance import Provenance, ProvenanceTracker
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.core.semantic_engine import SemanticEngine, SemanticFrame


@dataclass(frozen=True)
class StrategicPlan:
    objective: str
    phases: tuple[dict, ...]
    convergence_criteria: tuple[str, ...]
    rollback_points: tuple[str, ...]
    provenance: str = "PSEUDOCÓDIGO_HISTÓRICO_v1"


@dataclass(frozen=True)
class ComposedResult:
    transformed: str
    phase_results: tuple[dict, ...]
    rollback_triggered: bool
    metrics: dict
    provenance: str = "PSEUDOCÓDIGO_HISTÓRICO_v1"


@dataclass(frozen=True)
class PatternReport:
    dominant_direction: str
    verb_density: float
    keyword_coverage: float
    complexity_trend: str
    suggestions: tuple[str, ...]


@dataclass(frozen=True)
class RegistryOptimization:
    new_steps: tuple[str, ...]
    deprecated_steps: tuple[str, ...]
    improvements: tuple[str, ...]


class ITR_Extended(ITR):
    """Extensão do ITR com planejamento estratégico e auto-otimização."""

    NAME = "ITR_Extended"
    VERSION = "3.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.NUCLEAR
    DEPENDENCIES = ITR.DEPENDENCIES + ("ITR", "ETR_Extended")
    CYCLE_PHASES = ITR.CYCLE_PHASES

    # Passos adicionais
    EXTRA_STEPS: dict[str, Callable[[str], str]] = {
        "deep_structure": lambda t: (
            f"[ESTRUTURADO]\n{t}\n"
            f"[/ESTRUTURADO]\n"
            f"METADADOS: len={len(t)}"
        ),
        "ethical_align": lambda t: (
            t + "\n[ITR_Extended: alinhamento ético solicitado — validação ETR requerida]"
        ),
        "resilience_check": lambda t: (
            t + "\n[ITR_Extended: resiliência — rollback por snapshot habilitado]"
        ),
    }

    def __init__(self, provenance: ProvenanceTracker, safe_sandbox=None,
                 ethical_validator=None) -> None:
        super().__init__(provenance, safe_sandbox)
        self._semantic = SemanticEngine()
        self._ethical_validator = ethical_validator
        # Registra os passos extras no registry central
        for name, fn in self.EXTRA_STEPS.items():
            _STEP_REGISTRY.setdefault(name, fn)
        self._prov.register(
            "ITR_Extended.generate_strategic",
            Provenance.RECONSTRUCTED,
            "Extensão estratégica derivada de análise do ITR v2.1",
            source="itr_extended_v3",
        )

    # -----------------------------------------------------------------
    # 1. ANÁLISE SEMÂNTICA ESTRATÉGICA
    # -----------------------------------------------------------------

    def analyze_semantics(self, objective: str) -> SemanticFrame:
        return self._semantic.analyze(objective)

    def semantic_strategy_profile(self, objective: str) -> dict:
        frame = self.analyze_semantics(objective)
        relation_count = len(frame.relations)
        explicit_actions = [
            {
                "subject": r.subject,
                "action": r.action,
                "object": r.object,
                "negated": r.negated,
                "clause": r.clause_index,
            }
            for r in frame.relations
        ]
        return {
            "fingerprint": frame.fingerprint,
            "clauses": list(frame.clauses),
            "entities": list(frame.entities),
            "relations": explicit_actions,
            "relation_count": relation_count,
            "negation_count": len(frame.negations),
            "semantic_density": round(
                relation_count / max(len(frame.tokens), 1), 4
            ),
        }

    def validate_execution_semantics(self, original: str, transformed: str) -> dict:
        return self._semantic.compare(original, transformed)

    # -----------------------------------------------------------------
    # 1. PLANO ESTRATÉGICO
    # -----------------------------------------------------------------

    def generate_strategic(self, objective: str,
                            context: dict | None = None) -> StrategicPlan:
        """Gera plano multi-fase com critérios de convergência."""
        ctx = dict(context or {})
        self._analyze(objective)
        semantic = self.semantic_strategy_profile(objective)

        if ctx.get("clean_state"):
            # Estado já auditado como limpo: manter as quatro fases observáveis
            # sem voltar a transformar o conteúdo indefinidamente.
            phases = (
                {
                    "phase": 1, "name": "normalize",
                    "steps": ["normalize"],
                    "purpose": "estabilizar entrada sem alteração semântica",
                },
                {
                    "phase": 2, "name": "extract",
                    "steps": ["extract_keywords"],
                    "purpose": "observar núcleo semântico sem mutar o texto",
                    "semantic_profile": semantic,
                },
                {
                    "phase": 3, "name": "structure",
                    "steps": ["preserve"],
                    "purpose": "manter estrutura já estável",
                },
                {
                    "phase": 4, "name": "guard",
                    "steps": ["preserve"],
                    "purpose": "manter guardrails já estabilizados",
                },
            )
        else:
            phases = (
                {
                    "phase": 1, "name": "normalize",
                    "steps": ["normalize"],
                    "purpose": "estabilizar entrada",
                },
                {
                    "phase": 2, "name": "extract",
                    "steps": ["extract_keywords"],
                    "purpose": "isolar núcleo semântico",
                    "semantic_profile": semantic,
                },
                {
                    "phase": 3, "name": "structure",
                    "steps": ["structure", "deep_structure"],
                    "purpose": "organizar e enquadrar",
                },
                {
                    "phase": 4, "name": "guard",
                    "steps": ["guardrails", "ethical_align", "resilience_check"],
                    "purpose": "aplicar guardrails éticos e de resiliência",
                },
            )

        criteria = (
            "output_maior_que_input",
            "keywords_extraidas >= 3",
            "guardrails_presentes",
            "alinhamento_ético_confirmado",
        )
        rollbacks = ("after_phase_2", "after_phase_3")

        return StrategicPlan(
            objective=objective[:1000],
            phases=tuple(phases),
            convergence_criteria=criteria,
            rollback_points=rollbacks,
        )

    # -----------------------------------------------------------------
    # 2. EXECUÇÃO COMPOSTA
    # -----------------------------------------------------------------

    def execute_composed(self, plan: StrategicPlan,
                         initial_text: str | None = None) -> ComposedResult:
        """Executa plano com rollback transacional e métricas semânticas por fase."""
        text = plan.objective if initial_text is None else str(initial_text)
        phase_results: list[dict] = []
        rollback_triggered = False
        snapshot = text

        baseline = self.analyze_semantics(plan.objective)
        for phase in plan.phases:
            phase_metrics: dict = {"phase": phase["phase"], "name": phase["name"]}
            phase_start_len = len(text)
            semantic_violation = False
            try:
                for step_name in phase["steps"]:
                    fn = _STEP_REGISTRY.get(step_name)
                    if fn is None:
                        raise KeyError(f"passo '{step_name}' não registrado")

                    # "extract_keywords" é uma operação analítica: produz
                    # informação para o plano, mas não deve destruir a entrada.
                    # Mantemos o texto intacto e registramos o resultado na fase.
                    if step_name == "extract_keywords":
                        phase_metrics["extracted_keywords"] = [
                            k for k in _extract_keywords(text).split("|") if k
                        ]
                        continue

                    if step_name == "ethical_align":
                        if self._ethical_validator is None:
                            phase_metrics["ethical_status"] = "UNMEASURABLE"
                            text = fn(text)
                        else:
                            ethical = self._ethical_validator.validate_multi_framework(text)
                            phase_metrics["ethical_status"] = (
                                "VERIFIED" if ethical.approved else "BLOCKED"
                            )
                            phase_metrics["ethical_consensus"] = ethical.consensus_score
                            phase_metrics["ethical_dissent"] = list(ethical.dissenting_frameworks)
                            if not ethical.approved:
                                raise RuntimeError(
                                    f"ETR_REJECTED: consensus={ethical.consensus_score}"
                                )
                            text = text + "\n[ITR_Extended: alinhamento ético verificado pelo ETR_Extended]"
                        continue

                    text = fn(text)

                phase_metrics["rollback_available"] = True
                semantic_delta = self._semantic.compare(plan.objective, text)
                phase_metrics["semantic_relations_lost"] = len(semantic_delta["relations_lost"])
                phase_metrics["semantic_entities_lost"] = len(semantic_delta["entity_loss"])
                # Uma estratégia não pode apagar relações que estavam no objetivo.
                if semantic_delta["relations_lost"]:
                    semantic_violation = True
                    raise RuntimeError(
                        f"perda semântica na fase {phase['phase']}: "
                        f"{semantic_delta['relations_lost']}"
                    )

                phase_metrics["ok"] = True
                phase_metrics["delta_len"] = len(text) - phase_start_len
            except Exception as exc:
                phase_metrics["ok"] = False
                phase_metrics["error"] = str(exc)
                text = snapshot
                phase_metrics["rolled_back"] = True
                phase_metrics["blocking"] = True
                rollback_triggered = True
                phase_results.append(phase_metrics)
                break
            phase_results.append(phase_metrics)
            snapshot = text

        return ComposedResult(
            transformed=text,
            phase_results=tuple(phase_results),
            rollback_triggered=rollback_triggered,
            metrics={
                "input_len": len(plan.objective),
                "output_len": len(text),
                "phases": len(plan.phases),
                "rollbacks": sum(1 for p in phase_results if p.get("rolled_back")),
                "baseline_semantic_fingerprint": baseline.fingerprint,
                "semantic_guard_passed": not any(
                    p.get("semantic_relations_lost", 0) > 0 for p in phase_results
                ),
            },
        )

    # -----------------------------------------------------------------
    # 3. ANÁLISE DE PADRÕES
    # -----------------------------------------------------------------

    def analyze_patterns(self, objectives: list[str]) -> PatternReport:
        """Analisa padrões em múltiplos objetivos."""
        analyses = [self._analyze(o) for o in objectives]

        directions = [a["direction"] for a in analyses]
        dominant = max(set(directions), key=directions.count) if directions else "neutral"

        verb_counts = [len(a["verbs"]) for a in analyses]
        verb_density = sum(verb_counts) / max(len(analyses), 1)

        kw_coverage = sum(
            len(_extract_keywords(o).split("|")) if _extract_keywords(o) else 0
            for o in objectives
        ) / max(len(objectives), 1)

        complexities = [a["complexity"] for a in analyses]
        if complexities.count("alta") > len(complexities) / 2:
            trend = "crescente"
        elif complexities.count("simples") > len(complexities) / 2:
            trend = "decrescente"
        else:
            trend = "estável"

        suggestions: list[str] = []
        if verb_density < 1.0:
            suggestions.append("aumentar densidade de verbos de ação")
        if kw_coverage < 3.0:
            suggestions.append("enriquecer vocabulário dos objetivos")
        if dominant == "negative":
            suggestions.append("reduzir viés negativo ou equilibra-lo")
        if not suggestions:
            suggestions.append("objetivos equilibrados — manter")

        return PatternReport(
            dominant_direction=dominant,
            verb_density=round(verb_density, 3),
            keyword_coverage=round(kw_coverage, 3),
            complexity_trend=trend,
            suggestions=tuple(suggestions),
        )

    # -----------------------------------------------------------------
    # 4. OTIMIZAÇÃO DO REGISTRO
    # -----------------------------------------------------------------

    def optimize_registry(self) -> RegistryOptimization:
        """ITR propõe otimizações ao próprio registry de passos."""
        current = set(_STEP_REGISTRY.keys())
        proposed_new = {"semantic_expand", "context_inject"}
        deprecated: set[str] = set()
        improvements: list[str] = []

        if "structure" in current and "deep_structure" in current:
            improvements.append("structure e deep_structure podem ser compostos")

        if len(current) < 8:
            improvements.append("adicionar passos de enriquecimento semântico")

        return RegistryOptimization(
            new_steps=tuple(proposed_new),
            deprecated_steps=tuple(deprecated),
            improvements=tuple(improvements),
        )

    # -----------------------------------------------------------------
    # 5. PROPOSTA DE EVOLUÇÃO DA TRINDADE
    # -----------------------------------------------------------------

    def propose_trinity_evolution(self) -> list[dict]:
        """ITR propõe evoluções para ARA, ETR e para si mesmo."""
        return [
            {
                "target": "ARA",
                "proposal": "usar ITR.generate para escolher plano de regeneração",
                "reason": "regeneração guiada por estratégia explícita",
                "provenance": "INFERRED",
            },
            {
                "target": "ETR",
                "proposal": "receber variantes do ITR e recomendar a mais ética",
                "reason": "fechar o ciclo ética + estratégia",
                "provenance": "INFERRED",
            },
            {
                "target": "ITR_Extended",
                "proposal": "aprender quais passos maximizam consenso ético do ETR",
                "reason": "auto-otimização guiada por validação ética",
                "provenance": "INFERRED",
            },
        ]
