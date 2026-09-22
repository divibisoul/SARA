"""SARA — Memória: DNA Tags (proteção ontológica).
Status: IMPLEMENTED
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.clock import now_iso


PROTECTED_TAGS = ["🔒IDENTITY", "🔒ETHICS", "🔒MEMORY", "🔒CORE"]


@dataclass(frozen=True)
class GuardResult:
    blocked: bool
    reason: str = ""
    tags: tuple[str, ...] = ()


@dataclass
class ViolationRecord:
    operation: str
    tags: tuple[str, ...]
    timestamp: str


class DNA_Tags:
    NAME = "DNA_Tags"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.SECURITY
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.INGESTION,)

    PROTECTED: list[str] = list(PROTECTED_TAGS)

    def __init__(self) -> None:
        self._violations: list[ViolationRecord] = []

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
        }

    def scan(self, text: str) -> list[str]:
        s = str(text)
        return [tag for tag in self.PROTECTED if tag in s]

    def guard(self, operation: str, payload: Any) -> GuardResult:
        tags = tuple(self.scan(str(payload)))
        if tags:
            self._violations.append(
                ViolationRecord(operation, tags, now_iso())
            )
            return GuardResult(blocked=True, reason="tag_protegida", tags=tags)
        return GuardResult(blocked=False)

    def require_approval(self, tag: str, operation: str) -> dict:
        if tag not in self.PROTECTED:
            raise ValueError(f"tag '{tag}' não é protegida")
        return {"tag": tag, "operation": operation, "status": "requires_external_approval"}

    def violations(self) -> list[ViolationRecord]:
        return list(self._violations)

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("ingestion", self.NAME, True,
                       violations_count=len(self._violations))