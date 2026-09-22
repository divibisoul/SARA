"""SARA — Pesquisa: QuantumCrawler.
Status: PENDING_INFRASTRUCTURE
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


class CrawlBackend(Protocol):
    def fetch(self, query: str) -> list[dict]: ...


@dataclass
class TechCandidate:
    source: str
    name: str
    license: str
    description: str


class QuantumCrawler:
    NAME = "QuantumCrawler"
    VERSION = "1.0"
    STATUS = ModuleStatus.PENDING_INFRASTRUCTURE
    ROLE = CycleRole.RESEARCH
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.GOVERNANCE,)

    def __init__(self, backends: list[CrawlBackend]) -> None:
        self._backends = list(backends)

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "backends_configured": len(self._backends),
            "is_backends_ready": self.is_backends_ready(),
        }

    def is_backends_ready(self) -> bool:
        return len(self._backends) > 0

    def scan(self, query: str) -> list[TechCandidate]:
        raise NotImplementedError(
            "QuantumCrawler.scan requer backends reais de rede (GitHub API, "
            "HuggingFace API, arXiv API) com credenciais e rate limiting. "
            "Nenhum backend está configurado. "
            "Ativação: ver CANONICAL_ACTIVATION_PLAN.for_module('QuantumCrawler')."
        )

    def verify_source(self, candidate: TechCandidate) -> dict:
        raise NotImplementedError(
            "QuantumCrawler.verify_source requer acesso à rede para verificar "
            "autenticidade e licença da fonte. "
            "Ativação: ver CANONICAL_ACTIVATION_PLAN.for_module('QuantumCrawler')."
        )

    def list_sources(self) -> list[str]:
        return ["NVIDIA", "Tesla", "Google", "OpenAI", "HuggingFace"]

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, False,
                       reason="PENDING_INFRASTRUCTURE")