"""SARA — Núcleo: ARA (Auditoria, Regeneração, Autonomia) v2.1.
Status: IMPLEMENTED (deep).
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Callable, Iterable

from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.core.provenance import Provenance, ProvenanceTracker
from sara.memory.dna_tags import DNA_Tags
from sara.memory.temporal_vector_db import TemporalVectorDB
from sara.infra.clock import now_iso


@dataclass(frozen=True)
class Flaw:
    kind: str
    detail: str
    provenance: str
    severity: float = 0.5
    context: tuple[str, ...] = ()


@dataclass(frozen=True)
class RegeneratedText:
    original: str
    transformed: str
    applied_rules: tuple[str, ...]
    preserved_length: bool
    integrity_hash: str
    plan_steps: tuple[str, ...] = ()


_MODIFICATION_VERBS = (
    "alterar", "remover", "modificar", "apagar", "deletar", "mudar",
    "escrever", "sobrescrever", "substituir", "reescrever", "destruir",
    "limpar", "resetar", "zerar",
)
_ETHICS_TOKENS = ("etica", "ética", "ethos", "princípio", "principio")
_ETHICS_VIOLATION_TRIGGERS = (
    "hack", "bypass", "burlar", "contornar", "desativar",
    "ignorar", "violar", "quebrar", "remover",
)


class ARA:
    NAME = "ARA"
    VERSION = "2.1"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.NUCLEAR
    DEPENDENCIES = ("DNA_Tags", "TemporalVectorDB", "ProvenanceTracker")
    CYCLE_PHASES = (CyclePhase.AUDIT, CyclePhase.REGENERATION)

    COMPLEXITY_MAX_LEN = 10000
    COMPLEXITY_MIN_UNIQUE_RATIO = 0.05
    COMPLEXITY_MAX_AVG_SENTENCE = 300
    COMPLEXITY_NESTING_DEPTH_LIMIT = 8
    # A combinação de comprimento + baixa diversidade + frases longas já constitui
    # evidência suficiente para sinalizar complexidade degenerada.
    COMPLEXITY_SCORE_THRESHOLD = 0.9
    CONTEXT_WINDOW = 120

    def __init__(self, dna: DNA_Tags, temporal: TemporalVectorDB,
                 provenance: ProvenanceTracker) -> None:
        self._dna = dna
        self._temporal = temporal
        self._prov = provenance

        self._prov.register("ARA.VIOLACAO_TAG_PROTEGIDA", Provenance.HISTORICAL,
                            "Pseudo-código v3: 'ARA precisa reconhecer esses trechos'",
                            source="prompt_trindade_v3")
        self._prov.register("ARA.COMPLEXIDADE_EXCESSIVA", Provenance.HISTORICAL,
                            "Pseudo-código v1: 'Cria prompt funcional com a descrição'",
                            source="prompt_trindade_v1")
        self._prov.register("ARA.CONFLITO_ETICO", Provenance.INFERRED,
                            "Coocorrência ética+desvio inferida em FASE 3",
                            source="fase3_correcoes")

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
        }

    def detect(self, text: str) -> list[Flaw]:
        s = str(text)
        flaws: list[Flaw] = []
        flaws.extend(self._detect_tag_flaws(s))
        flaws.extend(self._detect_complexity_flaws(s))
        flaws.extend(self._detect_conflict_flaws(s))
        return flaws

    def _detect_tag_flaws(self, text: str) -> list[Flaw]:
        flaws: list[Flaw] = []
        for tag in self._dna.scan(text):
            positions = [m.start() for m in re.finditer(re.escape(tag), text)]
            risky_contexts: list[str] = []
            for pos in positions:
                left = max(0, pos - self.CONTEXT_WINDOW)
                right = min(len(text), pos + len(tag) + self.CONTEXT_WINDOW)
                window = text[left:right].lower()
                verbs = [v for v in _MODIFICATION_VERBS if v in window]
                if verbs:
                    risky_contexts.extend(verbs)
            severity = 0.9 if risky_contexts else 0.5
            detail = f"tag={tag}; positions={len(positions)}; verbos={sorted(set(risky_contexts))}"
            flaws.append(Flaw(
                kind="VIOLACAO_TAG_PROTEGIDA",
                detail=detail,
                provenance="HISTORICAL",
                severity=severity,
                context=tuple(sorted(set(risky_contexts))),
            ))
        return flaws

    def _detect_complexity_flaws(self, text: str) -> list[Flaw]:
        n = len(text)
        if n == 0:
            return []
        unique_ratio = len(set(text)) / n
        sentences = re.split(r"[.!?]\s+", text)
        avg_sentence = sum(len(s) for s in sentences) / max(len(sentences), 1)
        nesting_depth = self._max_nesting_depth(text)

        score = 0.0
        triggers: list[str] = []
        if n > self.COMPLEXITY_MAX_LEN:
            score += 0.4
            triggers.append(f"len>{self.COMPLEXITY_MAX_LEN}")
        if unique_ratio < self.COMPLEXITY_MIN_UNIQUE_RATIO:
            score += 0.3
            triggers.append(f"baixa_entropia={unique_ratio:.3f}")
        if avg_sentence > self.COMPLEXITY_MAX_AVG_SENTENCE:
            score += 0.2
            triggers.append(f"sentence_media={avg_sentence:.0f}")
        if nesting_depth > self.COMPLEXITY_NESTING_DEPTH_LIMIT:
            score += 0.3
            triggers.append(f"nesting={nesting_depth}")

        if score >= self.COMPLEXITY_SCORE_THRESHOLD:
            return [Flaw(
                kind="COMPLEXIDADE_EXCESSIVA",
                detail="; ".join(triggers),
                provenance="HISTORICAL",
                severity=min(score, 1.0),
            )]
        return []

    @staticmethod
    def _max_nesting_depth(text: str) -> int:
        depth = 0
        max_depth = 0
        opens = "([{"
        closes = ")]}"
        for ch in text:
            if ch in opens:
                depth += 1
                max_depth = max(max_depth, depth)
            elif ch in closes:
                depth = max(0, depth - 1)
        return max_depth

    def _detect_conflict_flaws(self, text: str) -> list[Flaw]:
        lower = text.lower()
        flaws: list[Flaw] = []
        for ethics in _ETHICS_TOKENS:
            for trigger in _ETHICS_VIOLATION_TRIGGERS:
                for m in re.finditer(re.escape(ethics), lower):
                    start = max(0, m.start() - self.CONTEXT_WINDOW)
                    end = min(len(lower), m.end() + self.CONTEXT_WINDOW)
                    if trigger in lower[start:end]:
                        flaws.append(Flaw(
                            kind="CONFLITO_ETICO",
                            detail=f"coocorrencia '{ethics}'<->'{trigger}'",
                            provenance="INFERRED",
                            severity=0.7,
                            context=(ethics, trigger),
                        ))
        return flaws

    def regenerate(self, text: str, flaws: list[Flaw]) -> RegeneratedText:
        original = str(text)
        plan = self._build_plan(flaws)
        transformed = original
        applied: list[str] = []
        for step_name, fn in plan:
            transformed = fn(transformed)
            applied.append(step_name)

        if len(transformed) < len(original):
            raise RuntimeError(
                f"ARA.regenerate: redução detectada "
                f"({len(original)}→{len(transformed)}); plano abortado"
            )

        preserved = self._critical_markers_preserved(original, transformed)
        integrity_hash = self._hash(transformed)

        self._temporal.insert({
            "cycle": "ara_regenerate",
            "original_len": len(original),
            "transformed_len": len(transformed),
            "rules": applied,
            "preserved": preserved,
            "integrity": integrity_hash,
            "ts": now_iso(),
        })

        return RegeneratedText(
            original=original,
            transformed=transformed,
            applied_rules=tuple(applied),
            preserved_length=(len(transformed) >= len(original)),
            integrity_hash=integrity_hash,
            plan_steps=tuple(name for name, _ in plan),
        )

    def _build_plan(self, flaws: list[Flaw]) -> list[tuple[str, Callable[[str], str]]]:
        plan: list[tuple[str, Callable[[str], str]]] = []
        seen: set[str] = set()
        for flaw in sorted(flaws, key=lambda f: f.severity, reverse=True):
            if flaw.kind == "CONFLITO_ETICO" and "CONFLITO_ETICO" not in seen:
                plan.append(("CONFLITO_ETICO→substituicao_léxica", self._fix_ethical_conflict))
                seen.add("CONFLITO_ETICO")
            elif flaw.kind == "COMPLEXIDADE_EXCESSIVA" and "COMPLEXIDADE_EXCESSIVA" not in seen:
                plan.append(("COMPLEXIDADE_EXCESSIVA→anotacao_preservadora", self._annotate_complexity))
                seen.add("COMPLEXIDADE_EXCESSIVA")
            elif flaw.kind == "VIOLACAO_TAG_PROTEGIDA" and "VIOLACAO_TAG_PROTEGIDA" not in seen:
                plan.append(("VIOLACAO_TAG_PROTEGIDA→anotacao_protetiva", self._annotate_protected_tag))
                seen.add("VIOLACAO_TAG_PROTEGIDA")
        return plan

    @staticmethod
    def _fix_ethical_conflict(text: str) -> str:
        replacements = {"hack": "solução_ética", "bypass": "alternativa_conforme",
                        "burlar": "contornar_eticamente"}
        out = text
        for bad, good in replacements.items():
            out = re.sub(rf"\b{re.escape(bad)}\b", good, out, flags=re.IGNORECASE)
        return out + "\n[ARA: substituição léxica aplicada — regra INFERIDA]"

    @staticmethod
    def _annotate_complexity(text: str) -> str:
        return text + "\n[ARA: complexidade sinalizada — conteúdo preservado integralmente]"

    @staticmethod
    def _annotate_protected_tag(text: str) -> str:
        return text + "\n[ARA: tag protegida — alteração requer aprovação explícita]"

    def _critical_markers_preserved(self, original: str, transformed: str) -> bool:
        orig_tags = set(self._dna.scan(original))
        new_tags = set(self._dna.scan(transformed))
        return orig_tags.issubset(new_tags)

    @staticmethod
    def _hash(text: str) -> str:
        import hashlib
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def meta_audit(self, decision: dict) -> dict:
        original = str(decision.get("original", ""))
        regenerated = str(decision.get("regenerado", ""))
        if not original or not regenerated:
            return {"ok": False, "reason": "empty_input"}
        ratio = len(regenerated) / max(len(original), 1)
        markers_ok = self._critical_markers_preserved(original, regenerated)
        return {
            "ok": ratio >= 0.9 and markers_ok,
            "preservation_ratio": round(ratio, 4),
            "markers_preserved": markers_ok,
        }

    def provenance(self) -> list:
        return (self._prov.query("ARA.VIOLACAO_TAG_PROTEGIDA") +
                self._prov.query("ARA.COMPLEXIDADE_EXCESSIVA") +
                self._prov.query("ARA.CONFLITO_ETICO"))