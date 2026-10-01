"""Complemento de recuperação lexical inspirado no DeerMem/DeerFlow.

Source provenance:
- bytedance/deer-flow
- backend/packages/harness/deerflow/agents/memory/backends/deermem/deermem/core/retrieval.py
- source commit: a619f8e0d0f01e0bdf993562e9f50624bf2df98c
- license at source: MIT

This module is additive. It does not replace TemporalVectorDB or
RegenerativeMemory. It provides an independent lexical retrieval index that
can later be composed with those memories by a higher-level selector.
"""

from __future__ import annotations

import math
import re
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sara.contracts.base import CyclePhase, CycleRole, ModuleStatus


@dataclass(frozen=True)
class LexicalFact:
    fact_id: str
    content: str
    category: str
    confidence: float
    created_at: str
    scope_user: str
    scope_agent: str
    source: str | None = None


class LexicalRetrieval:
    """SQLite FTS5 retrieval with BM25, confidence/time weighting and scope."""

    NAME = "LexicalRetrieval"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.MEMORY
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.PERSISTENCE,)

    _CONFIDENCE_WEIGHT = 0.2
    _TIME_DECAY_HALF_LIFE_DAYS = 30.0

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._lock = threading.RLock()
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=30000")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                fact_id UNINDEXED,
                content,
                category UNINDEXED,
                scope_user UNINDEXED,
                scope_agent UNINDEXED,
                created_at UNINDEXED,
                confidence UNINDEXED,
                source UNINDEXED
            )
            """
        )
        self._conn.commit()

    @staticmethod
    def _safe_match_query(query: str) -> str:
        tokens = [t for t in re.split(r"\s+", query.strip()) if t]
        if not tokens:
            return ""
        return " OR ".join(f'"{t.replace(chr(34), chr(34) * 2)}"' for t in tokens)

    @staticmethod
    def _age_days(created_at: str, now: datetime) -> float:
        try:
            raw = created_at.replace("Z", "+00:00")
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return max(0.0, (now - dt.astimezone(UTC)).total_seconds() / 86400.0)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _time_decay(cls, created_at: str, now: datetime) -> float:
        return math.exp(-math.log(2.0) * cls._age_days(created_at, now) / cls._TIME_DECAY_HALF_LIFE_DAYS)

    def index_fact(
        self,
        fact_id: str,
        content: str,
        *,
        category: str = "context",
        confidence: float = 0.5,
        created_at: str | None = None,
        scope_user: str = "",
        scope_agent: str = "",
        source: str | None = None,
    ) -> None:
        if not fact_id.strip():
            raise ValueError("LEXICAL_FACT_ID_REQUIRED")
        if not content.strip():
            raise ValueError("LEXICAL_CONTENT_REQUIRED")
        confidence = min(1.0, max(0.0, float(confidence)))
        created = created_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
        with self._lock:
            self._conn.execute("DELETE FROM memory_fts WHERE fact_id = ?", (fact_id,))
            self._conn.execute(
                """
                INSERT INTO memory_fts(
                    fact_id, content, category, scope_user, scope_agent,
                    created_at, confidence, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (fact_id, content, category, scope_user, scope_agent, created, confidence, source),
            )
            self._conn.commit()

    def remove_fact(self, fact_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM memory_fts WHERE fact_id = ?", (fact_id,))
            self._conn.commit()

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        scope_user: str | None = None,
        scope_agent: str | None = None,
        category: str | None = None,
    ) -> list[tuple[LexicalFact, float]]:
        if top_k < 1:
            raise ValueError("LEXICAL_TOP_K_INVALID")
        match = self._safe_match_query(query)
        if not match:
            return []

        clauses = ["memory_fts MATCH ?"]
        params: list[Any] = [match]
        if scope_user is not None:
            clauses.append("scope_user = ?")
            params.append(scope_user)
        if scope_agent is not None:
            clauses.append("scope_agent = ?")
            params.append(scope_agent)
        if category is not None:
            clauses.append("category = ?")
            params.append(category)

        sql = f"""
            SELECT fact_id, content, category, confidence, created_at,
                   scope_user, scope_agent, source, bm25(memory_fts) AS bm25_score
            FROM memory_fts
            WHERE {' AND '.join(clauses)}
            ORDER BY bm25_score
            LIMIT ?
        """
        params.append(max(top_k * 4, top_k))

        now = datetime.now(UTC)
        rows: list[tuple[LexicalFact, float]] = []
        with self._lock:
            raw_rows = self._conn.execute(sql, params).fetchall()

        for row in raw_rows:
            fact = LexicalFact(
                fact_id=row[0],
                content=row[1],
                category=row[2],
                confidence=float(row[3]),
                created_at=row[4],
                scope_user=row[5],
                scope_agent=row[6],
                source=row[7],
            )
            bm25 = max(0.0, -float(row[8]))
            score = bm25 * self._time_decay(fact.created_at, now) + fact.confidence * self._CONFIDENCE_WEIGHT
            rows.append((fact, score))

        rows.sort(key=lambda item: item[1], reverse=True)
        return rows[:top_k]

    def describe(self) -> dict[str, Any]:
        with self._lock:
            count = int(self._conn.execute("SELECT count(*) FROM memory_fts").fetchone()[0])
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [phase.value for phase in self.CYCLE_PHASES],
            "facts": count,
            "backend": "sqlite-fts5",
            "time_decay_half_life_days": self._TIME_DECAY_HALF_LIFE_DAYS,
        }

    def emit_trace(self, ctx: Any) -> None:
        if hasattr(ctx, "record"):
            ctx.record("persistence", self.NAME, True, facts=self.describe()["facts"])
