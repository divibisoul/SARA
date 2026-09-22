"""SARA — SemanticEngine v1.0.

Motor determinístico de análise semântica estrutural compartilhado por ARA,
ETR e ITR. Não depende de LLM e não reivindica compreensão humana: produz
frames verificáveis de cláusulas, entidades, ações, objetos, negações e
relações, preservando offsets e um fingerprint estável.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable


ACTION_VERBS = frozenset({
    "alterar", "apagar", "bloquear", "cancelar", "coletar", "criar",
    "deletar", "desenvolver", "executar", "expandir", "gerar", "integrar",
    "instalar", "limitar", "melhorar", "modificar", "otimizar", "produzir",
    "proteger", "preservar", "reduzir", "remover", "restaurar", "reescrever",
    "substituir", "validar", "vender", "violar", "analisar", "construir",
    "manter", "usar", "registrar", "armazenar", "enviar", "receber",
})

NEGATIONS = frozenset({"não", "nao", "nunca", "jamais", "sem", "nem"})

WORD_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int
    index: int


@dataclass(frozen=True)
class SemanticRelation:
    subject: str
    action: str
    object: str
    negated: bool
    clause_index: int
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class SemanticFrame:
    text_length: int
    clauses: tuple[str, ...]
    tokens: tuple[Token, ...]
    entities: tuple[str, ...]
    relations: tuple[SemanticRelation, ...]
    negations: tuple[str, ...]
    fingerprint: str


class SemanticEngine:
    VERSION = "1.0"

    @staticmethod
    def normalize(text: str) -> str:
        return re.sub(r"\s+", " ", str(text)).strip()

    @classmethod
    def tokenize(cls, text: str) -> tuple[Token, ...]:
        s = str(text)
        return tuple(
            Token(m.group(0), m.start(), m.end(), i)
            for i, m in enumerate(WORD_RE.finditer(s))
        )

    @classmethod
    def split_clauses(cls, text: str) -> tuple[str, ...]:
        normalized = cls.normalize(text)
        if not normalized:
            return ()
        clauses = re.split(r"(?<=[.!?;])\s+|\n+", normalized)
        return tuple(part.strip() for part in clauses if part.strip())

    @classmethod
    def extract_entities(cls, text: str) -> tuple[str, ...]:
        candidates: list[str] = []

        for pattern in (
            r'"([^"]+)"',
            r"'([^']+)'",
            r"\b[A-ZÀ-Ý][\wÀ-ÿ]*(?:[-_][\wÀ-ÿ]+)*\b",
            r"\b[A-Z][A-Z0-9_]{2,}\b",
        ):
            candidates.extend(re.findall(pattern, str(text)))

        seen: list[str] = []
        for item in candidates:
            value = str(item).strip()
            if value and value.lower() not in {x.lower() for x in seen}:
                seen.append(value)
        return tuple(seen)

    @classmethod
    def _relations_for_clause(cls, clause: str, clause_index: int) -> list[SemanticRelation]:
        tokens = [t.text.lower() for t in cls.tokenize(clause)]
        relations: list[SemanticRelation] = []
        if not tokens:
            return relations

        for i, token in enumerate(tokens):
            if token not in ACTION_VERBS:
                continue
            before = tokens[max(0, i - 4):i]
            after = tokens[i + 1:i + 7]
            subject = next(
                (t for t in reversed(before) if t not in NEGATIONS),
                "implicit",
            )
            obj = next(
                (t for t in after if t not in NEGATIONS),
                "implicit",
            )
            negated = any(t in NEGATIONS for t in before[-3:])
            evidence = tuple(tokens[max(0, i - 2):min(len(tokens), i + 4)])
            relations.append(
                SemanticRelation(
                    subject=subject,
                    action=token,
                    object=obj,
                    negated=negated,
                    clause_index=clause_index,
                    evidence=evidence,
                )
            )
        return relations

    @classmethod
    def analyze(cls, text: str) -> SemanticFrame:
        s = str(text)
        clauses = cls.split_clauses(s)
        tokens = cls.tokenize(s)
        relations: list[SemanticRelation] = []
        for index, clause in enumerate(clauses):
            relations.extend(cls._relations_for_clause(clause, index))
        negations = tuple(t.text.lower() for t in tokens if t.text.lower() in NEGATIONS)
        entities = cls.extract_entities(s)
        canonical = {
            "clauses": clauses,
            "tokens": [(t.text.lower(), t.start, t.end) for t in tokens],
            "entities": entities,
            "relations": [
                (r.subject, r.action, r.object, r.negated, r.clause_index)
                for r in relations
            ],
            "negations": negations,
        }
        digest = hashlib.sha256(repr(canonical).encode("utf-8")).hexdigest()
        return SemanticFrame(
            text_length=len(s),
            clauses=clauses,
            tokens=tokens,
            entities=entities,
            relations=tuple(relations),
            negations=negations,
            fingerprint=digest,
        )

    @staticmethod
    def relation_signature(frame: SemanticFrame) -> tuple[tuple[str, str, str, bool], ...]:
        return tuple(
            (r.subject, r.action, r.object, r.negated)
            for r in frame.relations
        )

    @classmethod
    def compare(cls, before: str, after: str) -> dict:
        a = cls.analyze(before)
        b = cls.analyze(after)
        rel_a = set(cls.relation_signature(a))
        rel_b = set(cls.relation_signature(b))
        return {
            "before_fingerprint": a.fingerprint,
            "after_fingerprint": b.fingerprint,
            "relations_preserved": sorted(rel_a & rel_b),
            "relations_lost": sorted(rel_a - rel_b),
            "relations_added": sorted(rel_b - rel_a),
            "entity_overlap": sorted(set(a.entities) & set(b.entities)),
            "entity_loss": sorted(set(a.entities) - set(b.entities)),
            "entity_gain": sorted(set(b.entities) - set(a.entities)),
        }
