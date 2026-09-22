"""SARA — Pesquisa: QuantumScanner.
Status: PENDING_INFRASTRUCTURE
"""
from __future__ import annotations
from typing import Literal
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


class QuantumScanner:
    NAME = "QuantumScanner"
    VERSION = "1.0"
    STATUS = ModuleStatus.PENDING_INFRASTRUCTURE
    ROLE = CycleRole.RESEARCH
    DEPENDENCIES = ()
    CYCLE_PHASES = ()

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "target_access_ready": self.is_target_access_ready(),
        }

    def is_target_access_ready(self) -> bool:
        return False

    def scan(self, target: str,
             depth: Literal["shallow", "deep", "atomic"] = "shallow") -> dict:
        raise NotImplementedError(
            "QuantumScanner.scan requer acesso a binário/código-fonte do alvo e "
            "ferramentas de análise profunda (parsers, disassemblers). "
            "Ativação: ver CANONICAL_ACTIVATION_PLAN.for_module('QuantumScanner')."
        )

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, False,
                       reason="PENDING_INFRASTRUCTURE")