"""SARA — Núcleo: ITR (Inovação, Tecnologia, Resiliência) v2.1.
Status: IMPLEMENTED (deep).
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Callable, Literal

from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.core.provenance import Provenance, ProvenanceTracker


@dataclass(frozen=True)
class Strategy:
    objective: str
    variant: str
    plan: tuple[str, ...]
    alternatives: tuple[dict, ...]
    context_used: bool
    analysis: dict
    provenance: str = "PSEUDOCÓDIGO_HISTÓRICO_v1"


@dataclass(frozen=True)
class ExecutionResult:
    transformed: str
    status: str
    capability_level: str
    steps_applied: tuple[str, ...]
    metrics: dict
    provenance: str = "PSEUDOCÓDIGO_HISTÓRICO_v1"


_ACTION_VERBS = (
    "promover", "criar", "expandir", "reduzir", "otimizar", "integrar",
    "validar", "gerar", "analisar", "construir", "remover", "ajustar",
    "melhorar", "proteger", "preservar", "restaurar",
)

_DIRECTION_TOKENS = {
    "positive": ("promover", "criar", "expandir", "melhorar", "integrar",
                 "proteger", "preservar", "restaurar"),
    "negative": ("reduzir", "remover", "eliminar", "bloquear", "impedir"),
    "neutral": ("analisar", "validar", "ajustar", "otimizar"),
}

_STOPWORDS = frozenset({
    "de", "da", "do", "das", "dos", "a", "o", "as", "os",
    "e", "ou", "para", "com", "em", "no", "na", "um", "uma",
    "que", "se", "por", "ao", "à", "é",
})


def _normalize(text: str) -> str:
    s = re.sub(r"\s+", " ", text).strip()
    s = re.sub(r"([.!?])\1+", r"\1", s)
    return s


def _extract_keywords(text: str, top: int = 5) -> str:
    tokens = re.findall(r"[\wÀ-ÿ]+", text.lower())
    keywords = [t for t in tokens if t not in _STOPWORDS and len(t) > 3]
    seen: list[str] = []
    for k in keywords:
        if k not in seen:
            seen.append(k)
    return "|".join(seen[:top])


def _structure_objective(text: str) -> str:
    keywords = _extract_keywords(text)
    return (
        f"OBJETIVO: {text}\n"
        f"CONTEXTO: derivado de análise de intenção\n"
        f"PALAVRAS_CHAVE: {keywords}"
    )


def _add_guardrails(text: str) -> str:
    return text + (
        "\nGUARDRAILS:"
        "\n- preservar conteúdo original"
        "\n- registrar cada passo"
        "\n- rollback disponível em falha"
    )


_STEP_REGISTRY: dict[str, Callable[[str], str]] = {
    "normalize": _normalize,
    "extract_keywords": _extract_keywords,
    "structure": _structure_objective,
    "guardrails": _add_guardrails,
}


class ITR:
    NAME = "ITR"
    VERSION = "2.1"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.NUCLEAR
    DEPENDENCIES = ("ProvenanceTracker",)
    CYCLE_PHASES = (CyclePhase.STRATEGY, CyclePhase.EXECUTION)

    def __init__(self, provenance: ProvenanceTracker, safe_sandbox=None) -> None:
        self._prov = provenance
        self._safe_sandbox = safe_sandbox
        self._prov.register("ITR.generate", Provenance.HISTORICAL,
                            "Pseudo-código v1: 'Cria novas estratégias baseadas em objetivos'")
        self._prov.register("ITR.execute", Provenance.HISTORICAL,
                            "Pseudo-código v1: 'Implementa a estratégia com resiliência'")

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "safe_sandbox_attached": self._safe_sandbox is not None,
        }

    def _analyze(self, objective: str) -> dict:
        lower = objective.lower()
        tokens = re.findall(r"[\wÀ-ÿ]+", lower)
        verbs = [v for v in _ACTION_VERBS if v in tokens]
        direction = self._direction(lower)
        complexity = self._complexity(objective)
        word_count = len(tokens)
        return {"verbs": tuple(verbs), "direction": direction,
                "complexity": complexity, "word_count": word_count}

    @staticmethod
    def _direction(lower: str) -> Literal["positive", "negative", "neutral"]:
        for direction, tokens in _DIRECTION_TOKENS.items():
            for t in tokens:
                if re.search(rf"\b{re.escape(t)}\b", lower):
                    return direction
        return "neutral"

    @staticmethod
    def _complexity(objective: str) -> str:
        n = len(objective.split())
        if n <= 6:
            return "simples"
        if n <= 20:
            return "media"
        return "alta"

    def generate(self, objective: str, context: dict | None = None) -> Strategy:
        ctx = dict(context or {})
        analysis = self._analyze(objective)
        variants = self._produce_variants(analysis, ctx)
        primary = self._select_primary(variants, analysis, ctx)
        return Strategy(
            objective=str(objective)[:1000],
            variant=primary["variant"],
            plan=tuple(primary["plan"]),
            alternatives=tuple(variants),
            context_used=bool(ctx),
            analysis=analysis,
        )

    def _produce_variants(self, analysis: dict, ctx: dict) -> list[dict]:
        base = ["normalize", "structure"]
        if analysis["complexity"] == "alta":
            base = ["normalize", "extract_keywords", "structure", "guardrails"]
        elif analysis["complexity"] == "media":
            base = ["normalize", "structure", "guardrails"]
        return [
            {"variant": "conservadora", "plan": ["normalize"],
             "description": "transformação mínima"},
            {"variant": "equilibrada", "plan": base,
             "description": "normalização + estruturação"},
            {"variant": "agressiva",
             "plan": ["normalize", "extract_keywords", "structure", "guardrails"],
             "description": "extrai e reestrutura"},
        ]

    @staticmethod
    def _select_primary(variants: list[dict], analysis: dict, ctx: dict) -> dict:
        forced = ctx.get("force_variant")
        if forced:
            for v in variants:
                if v["variant"] == forced:
                    return v
        if analysis["direction"] == "negative":
            return next(v for v in variants if v["variant"] == "conservadora")
        return next(v for v in variants if v["variant"] == "equilibrada")

    def execute(self, strategy: Strategy) -> ExecutionResult:
        if self._safe_sandbox is not None:
            analysis = self._safe_sandbox.analyze_static(strategy.objective)
            if analysis.vulnerabilities:
                raise RuntimeError(
                    f"ITR.execute: sandbox detectou vulnerabilidades: {analysis.vulnerabilities}"
                )
        text = strategy.objective
        metrics: dict = {"input_len": len(text)}
        steps_applied: list[str] = []
        for step_name in strategy.plan:
            fn = _STEP_REGISTRY.get(step_name)
            if fn is None:
                raise KeyError(f"ITR.execute: passo '{step_name}' não registrado")
            text = fn(text)
            steps_applied.append(step_name)
        metrics["output_len"] = len(text)
        metrics["steps_count"] = len(steps_applied)
        metrics["execution_scope"] = "local_registered_transformations"
        metrics["sandbox_static_checked"] = self._safe_sandbox is not None
        return ExecutionResult(
            transformed=text, status="executed", capability_level="LOCAL_TRANSFORMATION",
            steps_applied=tuple(steps_applied), metrics=metrics,
        )

    def provenance(self) -> list:
        return self._prov.query("ITR.generate") + self._prov.query("ITR.execute")