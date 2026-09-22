"""SARA — camada adicional de auto-otimização da Trindade.

Não substitui ARA, ETR, ITR ou TrinitySynergy.
Orquestra as capacidades já existentes para executar:
  ARA -> ARA/ETR/ITR (auditoria estrutural)
  ETR -> ARA/ITR (validação multi-framework)
  ITR -> ARA/ETR (análise de padrões e propostas)
  TrinitySynergy -> ciclo convergente da própria Trindade

A camada é observacional por padrão: ela produz evidência e propostas, sem
alterar automaticamente as regras dos módulos existentes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sara.core.ara_extended import ARA_Extended
from sara.core.etr_extended import ETR_Extended
from sara.core.itr_extended import ITR_Extended
from sara.core.trinity_synergy import TrinityReport, TrinitySynergy
from sara.infra.hashing import hash_json


@dataclass(frozen=True)
class TrinitySelfOptimizationReport:
    """Relatório fechado de uma rodada de auto-otimização da Trindade."""

    passes: int
    converged: bool
    stable: bool
    ara_self: dict[str, Any]
    etr_self: dict[str, Any]
    itr_self: dict[str, Any]
    ara_cross_audit: dict[str, Any]
    etr_cross_validation: dict[str, Any]
    itr_cross_analysis: dict[str, Any]
    trinity_cycle: dict[str, Any]
    proposals: dict[str, list[Any]]
    findings: tuple[str, ...]
    integrity_hash: str


class TrinitySelfOptimizer:
    """Executa a autoaplicação coordenada sem substituir os módulos nucleares."""

    NAME = "TrinitySelfOptimizer"
    VERSION = "1.0"
    MAX_PASSES = 3

    def __init__(
        self,
        ara: ARA_Extended,
        etr: ETR_Extended,
        itr: ITR_Extended,
        synergy: TrinitySynergy | None = None,
        max_passes: int = 2,
    ) -> None:
        if max_passes < 1:
            raise ValueError("max_passes deve ser >= 1")
        if max_passes > self.MAX_PASSES:
            raise ValueError(f"max_passes deve ser <= {self.MAX_PASSES}")

        self._ara = ara
        self._etr = etr
        self._itr = itr
        self._synergy = synergy or TrinitySynergy(ara, etr, itr)
        self._history: list[TrinitySelfOptimizationReport] = []

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "max_passes": self.MAX_PASSES,
            "mode": "observational_additive",
            "modules": ["ARA_Extended", "ETR_Extended", "ITR_Extended", "TrinitySynergy"],
        }

    @staticmethod
    def _plain(value: Any) -> Any:
        if hasattr(value, "items"):
            return {str(k): TrinitySelfOptimizer._plain(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set, frozenset)):
            return [TrinitySelfOptimizer._plain(v) for v in value]
        if hasattr(value, "__dataclass_fields__"):
            return TrinitySelfOptimizer._plain(asdict(value))
        return value

    def _run_pass(self) -> dict[str, Any]:
        # 1. ARA sobre ARA.
        ara_self = self._ara.applied_to_self()

        # 2. ETR sobre ETR.
        etr_self_result = self._etr.validate_against_self()
        etr_self = self._plain(etr_self_result)

        # 3. ITR sobre ITR, usando análise de seus próprios artefatos.
        itr_self_result = self._itr.optimize_registry()
        itr_self = self._plain(itr_self_result)
        itr_pattern = self._itr.analyze_patterns([
            self._plain_text(ara_self),
            self._plain_text(etr_self),
            self._plain_text(itr_self),
        ])
        itr_cross = {
            "optimization": itr_self,
            "pattern_analysis": self._plain(itr_pattern),
            "trinity_evolution": self._itr.propose_trinity_evolution(),
        }

        # 4. ARA sobre ETR e ITR.
        ara_cross = {
            "etr_structural": [
                self._plain(f) for f in self._ara.detect_structural(self._plain_text(etr_self))
            ],
            "itr_structural": [
                self._plain(f) for f in self._ara.detect_structural(self._plain_text(itr_self))
            ],
            "etr_relational": [
                self._plain(f) for f in self._ara.detect_relational(self._plain_text(etr_self))
            ],
            "itr_relational": [
                self._plain(f) for f in self._ara.detect_relational(self._plain_text(itr_self))
            ],
        }

        # 5. ETR sobre ARA e ITR.
        etr_cross = self._etr.validate_trinity(
            ara_output=self._plain_text(ara_self),
            itr_output=self._plain_text(itr_self),
        )

        # 6. TrinitySynergy sobre a Trindade completa.
        synergy_report = self._synergy.apply_to_self()
        trinity_cycle = self._plain_trinity_report(synergy_report)

        findings = self._collect_findings(
            ara_self=ara_self,
            etr_self=etr_self_result,
            ara_cross=ara_cross,
            etr_cross=etr_cross,
            trinity_cycle=trinity_cycle,
        )

        proposals = {
            "ARA": self._plain(self._ara.propose_rule_upgrade()),
            "ETR": self._plain(self._etr.propose_ethical_upgrade()),
            "ITR": self._plain(self._itr.propose_trinity_evolution()),
            "ITR_registry": self._plain(self._itr.optimize_registry()),
        }

        return {
            "ara_self": self._plain(ara_self),
            "etr_self": etr_self,
            "itr_self": itr_self,
            "ara_cross_audit": ara_cross,
            "etr_cross_validation": self._plain(etr_cross),
            "itr_cross_analysis": self._plain(itr_cross),
            "trinity_cycle": trinity_cycle,
            "proposals": proposals,
            "findings": tuple(findings),
        }

    @staticmethod
    def _plain_text(value: Any) -> str:
        return str(TrinitySelfOptimizer._plain(value))

    @staticmethod
    def _plain_trinity_report(report: TrinityReport) -> dict[str, Any]:
        iterations = []
        for iteration in report.iterations:
            iterations.append({
                "iteration": iteration.iteration,
                "ara_flaws": list(iteration.ara_flaws),
                "ara_structural": list(iteration.ara_structural),
                "ara_relational": list(iteration.ara_relational),
                "itr_plan_phases": iteration.itr_plan_phases,
                "etr_consensus": iteration.etr_consensus,
                "etr_dissenting": list(iteration.etr_dissenting),
                "regenerated": iteration.regenerated,
                "executed": iteration.executed,
                "converged": iteration.converged,
                "details": TrinitySelfOptimizer._plain(iteration.details),
            })
        return {
            "target": report.target,
            "iterations": iterations,
            "final_text": report.final_text,
            "converged": report.converged,
            "total_iterations": report.total_iterations,
            "self_audit": TrinitySelfOptimizer._plain(report.self_audit),
        }

    @staticmethod
    def _collect_findings(
        *,
        ara_self: dict[str, Any],
        etr_self: Any,
        ara_cross: dict[str, Any],
        etr_cross: dict[str, Any],
        trinity_cycle: dict[str, Any],
    ) -> list[str]:
        findings: list[str] = []

        for kind in ara_self.get("flaws", []):
            findings.append(f"ARA_SELF:{kind}")
        for kind in ara_self.get("structural_flaws", []):
            findings.append(f"ARA_SELF_STRUCTURAL:{kind}")

        dissenting = getattr(etr_self, "dissenting_frameworks", ())
        findings.extend(f"ETR_SELF_DISSENT:{name}" for name in dissenting)

        for side in ("etr_structural", "itr_structural", "etr_relational", "itr_relational"):
            for item in ara_cross.get(side, []):
                if isinstance(item, dict) and item.get("kind"):
                    findings.append(f"ARA_CROSS:{side}:{item['kind']}")

        combined = etr_cross.get("combined", {})
        if combined and not combined.get("approved", False):
            findings.append("ETR_CROSS:combined_rejected")

        if not trinity_cycle.get("converged", False):
            findings.append("TRINITY_CYCLE:not_converged")

        return findings

    def run(self, max_passes: int | None = None) -> TrinitySelfOptimizationReport:
        """Executa rodadas reais de autoaplicação até estabilização do relatório."""
        passes = self.MAX_PASSES if max_passes is None else int(max_passes)
        if passes < 1 or passes > self.MAX_PASSES:
            raise ValueError(f"max_passes deve estar entre 1 e {self.MAX_PASSES}")

        previous_hash: str | None = None
        stable = False
        last_payload: dict[str, Any] | None = None

        for index in range(1, passes + 1):
            payload = self._run_pass()
            digest = hash_json({
                "ara_self": payload["ara_self"],
                "etr_self": payload["etr_self"],
                "itr_self": payload["itr_self"],
                "ara_cross_audit": payload["ara_cross_audit"],
                "etr_cross_validation": payload["etr_cross_validation"],
                "itr_cross_analysis": payload["itr_cross_analysis"],
                "trinity_cycle": payload["trinity_cycle"],
                "proposals": payload["proposals"],
                "findings": payload["findings"],
            })

            stable = previous_hash == digest
            last_payload = payload
            previous_hash = digest

            if stable:
                final = TrinitySelfOptimizationReport(
                    passes=index,
                    converged=bool(payload["trinity_cycle"].get("converged", False))
                    and not payload["findings"],
                    stable=True,
                    ara_self=payload["ara_self"],
                    etr_self=payload["etr_self"],
                    itr_self=payload["itr_self"],
                    ara_cross_audit=payload["ara_cross_audit"],
                    etr_cross_validation=payload["etr_cross_validation"],
                    itr_cross_analysis=payload["itr_cross_analysis"],
                    trinity_cycle=payload["trinity_cycle"],
                    proposals=payload["proposals"],
                    findings=tuple(payload["findings"]),
                    integrity_hash=digest,
                )
                self._history.append(final)
                return final

        assert last_payload is not None
        final = TrinitySelfOptimizationReport(
            passes=passes,
            converged=bool(last_payload["trinity_cycle"].get("converged", False))
            and not last_payload["findings"],
            stable=stable,
            ara_self=last_payload["ara_self"],
            etr_self=last_payload["etr_self"],
            itr_self=last_payload["itr_self"],
            ara_cross_audit=last_payload["ara_cross_audit"],
            etr_cross_validation=last_payload["etr_cross_validation"],
            itr_cross_analysis=last_payload["itr_cross_analysis"],
            trinity_cycle=last_payload["trinity_cycle"],
            proposals=last_payload["proposals"],
            findings=tuple(last_payload["findings"]),
            integrity_hash=previous_hash or "",
        )
        self._history.append(final)
        return final

    def history(self) -> list[TrinitySelfOptimizationReport]:
        return list(self._history)


def from_sara_system(system: Any, max_passes: int = 2) -> TrinitySelfOptimizer:
    """Cria a camada diretamente dos componentes reais de SaraSystem."""
    components = system.components
    return TrinitySelfOptimizer(
        ara=components["ara_extended"],
        etr=components["etr_extended"],
        itr=components["itr_extended"],
        synergy=components.get("trinity"),
        max_passes=max_passes,
    )
