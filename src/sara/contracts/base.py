"""SARA — Contratos base entre todos os módulos.
Status: IMPLEMENTED (foundational).
"""
from __future__ import annotations
from enum import Enum
from typing import Protocol, runtime_checkable

CONTRACT_VERSION = "3.1"


class ModuleStatus(str, Enum):
    IMPLEMENTED = "IMPLEMENTED"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_INFRASTRUCTURE = "PENDING_INFRASTRUCTURE"


class CyclePhase(str, Enum):
    INGESTION = "ingestion"
    AUDIT = "audit"
    REGENERATION = "regeneration"
    IDENTITY = "identity"
    ETHICS = "ethics"
    STRATEGY = "strategy"
    EXECUTION = "execution"
    VALIDATION = "validation"
    PERSISTENCE = "persistence"
    SNAPSHOT = "snapshot"
    MONITORING = "monitoring"
    GOVERNANCE = "governance"


class CycleRole(str, Enum):
    NUCLEAR = "nuclear"
    MEMORY = "memory"
    SECURITY = "security"
    REGENERATION = "regeneration"
    MONITORING = "monitoring"
    RESEARCH = "research"
    GOVERNANCE = "governance"
    META = "meta"


@runtime_checkable
class SaraModule(Protocol):
    NAME: str
    VERSION: str
    STATUS: ModuleStatus
    ROLE: CycleRole
    DEPENDENCIES: tuple[str, ...]
    CYCLE_PHASES: tuple[CyclePhase, ...]

    def describe(self) -> dict:
        ...


@runtime_checkable
class Traceable(Protocol):
    def emit_trace(self, ctx: "CycleContextProtocol") -> None:
        ...