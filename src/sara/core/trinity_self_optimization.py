"""SARA — auto-otimização integrada da Trindade ARA/ETR/ITR com ERU.

Camada aditiva e observacional. Usa somente componentes reais do SaraSystem,
produz evidência, propostas e estabilidade do relatório sem modificar
automaticamente as regras dos núcleos.
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
    NAME = "TrinitySelfOptimizer"
    VERSION = "1.1"
    MAX_PASSES = 3

    def __init__(
        self,
        ara: ARA_Extended,
        etr: ETR_Extended,
        itr: ITR_Extended,
        synergy: TrinitySynergy | None = None,
        max_passes: int = 2,
    ) -> None:
        if max_passes < 1 or max_passes > self.MAX_PASSES:
            raise ValueError(f"max_passes deve estar entre 1 e {self.MAX_PASSES}")
        self._ara = ara
        self._etr = etr
        self._itr = itr
        self._synergy = synergy or TrinitySynergy(ara, etr, itr)
        self._max_passes = max_passes
        self._history: list[TrinitySelfOptimizationReport] = []

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "max_passes": self._max_passes,
            "mode": "observational_additive",
            "modules": [
                "ARA_Extended", "ETR_Extended", "ITR_Extended", "TrinitySynergy"
            ],
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

    @staticmethod
    def _plain_text(value: Any) -> str:
        return str(TrinitySelfOptimizer._plain(value))

    @staticmethod
    def _plain_trinity_report(report: TrinityReport) -> dict[str, Any]:
        return {
            "target": report.target,
            "iterations": [
                {
                    "iteration": item.iteration,
                    "ara_flaws": list(item.ara_flaws),
                    "ara_structural": list(item.ara_structural),
                    "ara_relational": list(item.ara_relational),
                    "itr_plan_phases": item.itr_plan_phases,
                    "etr_consensus": item.etr_consensus,
                    "etr_dissenting": list(item.etr_dissenting),
                    "regenerated": item.regenerated,
                    "executed": item.executed,
                    "converged": item.converged,
                    "details": TrinitySelfOptimizer._plain(item.details),
                }
                for item in report.iterations
            ],
            "final_text": report.final_text,
            "converged": report.converged,
            "total_iterations": report.total_iterations,
            "self_audit": TrinitySelfOptimizer._plain(report.self_audit),
        }

    def _run_pass(self) -> dict[str, Any]:
        ara_self = self._ara.applied_to_self()
        etr_self_result = self._etr.validate_against_self()
        itr_self_result = self._itr.optimize_registry()

        itr_cross = {
            "optimization": self._plain(itr_self_result),
            "pattern_analysis": self._plain(self._itr.analyze_patterns([
                self._plain_text(ara_self),
                self._plain_text(etr_self_result),
                self._plain_text(itr_self_result),
            ])),
            "trinity_evolution": self._itr.propose_trinity_evolution(),
        }

        ara_cross = {
            "etr_structural": [
                self._plain(x)
                for x in self._ara.detect_structural(self._plain_text(etr_self_result))
            ],
            "itr_structural": [
                self._plain(x)
                for x in self._ara.detect_structural(self._plain_text(itr_self_result))
            ],
            "etr_relational": [
                self._plain(x)
                for x in self._ara.detect_relational(self._plain_text(etr_self_result))
            ],
            "itr_relational": [
                self._plain(x)
                for x in self._ara.detect_relational(self._plain_text(itr_self_result))
            ],
        }

        etr_cross = self._etr.validate_trinity(
            self._plain_text(ara_self),
            self._plain_text(itr_self_result),
        )
        synergy_report = self._synergy.apply_to_self()
        trinity_cycle = self._plain_trinity_report(synergy_report)

        findings: list[str] = []
        findings.extend(f"ARA_SELF:{x}" for x in ara_self.get("flaws", []))
        findings.extend(
            f"ARA_SELF_STRUCTURAL:{x}" for x in ara_self.get("structural_flaws", [])
        )
        findings.extend(
            f"ETR_SELF_DISSENT:{x}" for x in etr_self_result.dissenting_frameworks
        )
        if etr_cross.get("combined", {}).get("approved") is False:
            findings.append("ETR_CROSS:combined_rejected")
        if not trinity_cycle.get("converged", False):
            findings.append("TRINITY_CYCLE:not_converged")
        for side in (
            "etr_structural", "itr_structural", "etr_relational", "itr_relational"
        ):
            for item in ara_cross[side]:
                if isinstance(item, dict) and item.get("kind"):
                    findings.append(f"ARA_CROSS:{side}:{item['kind']}")

        proposals = {
            "ARA": self._plain(self._ara.propose_rule_upgrade()),
            "ETR": self._plain(self._etr.propose_ethical_upgrade()),
            "ITR": self._plain(self._itr.propose_trinity_evolution()),
            "ITR_registry": self._plain(self._itr.optimize_registry()),
        }

        return {
            "ara_self": self._plain(ara_self),
            "etr_self": self._plain(etr_self_result),
            "itr_self": self._plain(itr_self_result),
            "ara_cross_audit": ara_cross,
            "etr_cross_validation": self._plain(etr_cross),
            "itr_cross_analysis": self._plain(itr_cross),
            "trinity_cycle": trinity_cycle,
            "proposals": proposals,
            "findings": tuple(findings),
        }

    def run(self, max_passes: int | None = None) -> TrinitySelfOptimizationReport:
        passes = self._max_passes if max_passes is None else int(max_passes)
        if passes < 1 or passes > self.MAX_PASSES:
            raise ValueError(f"max_passes deve estar entre 1 e {self.MAX_PASSES}")

        previous_hash: str | None = None
        last: dict[str, Any] | None = None
        stable = False

        for index in range(1, passes + 1):
            payload = self._run_pass()
            digest = hash_json(payload)
            stable = previous_hash == digest
            previous_hash = digest
            last = payload
            if stable:
                break

        assert last is not None
        final = TrinitySelfOptimizationReport(
            passes=index,
            converged=bool(last["trinity_cycle"].get("converged")) and not last["findings"],
            stable=stable,
            ara_self=last["ara_self"],
            etr_self=last["etr_self"],
            itr_self=last["itr_self"],
            ara_cross_audit=last["ara_cross_audit"],
            etr_cross_validation=last["etr_cross_validation"],
            itr_cross_analysis=last["itr_cross_analysis"],
            trinity_cycle=last["trinity_cycle"],
            proposals=last["proposals"],
            findings=tuple(last["findings"]),
            integrity_hash=previous_hash or "",
        )
        self._history.append(final)
        return final

    def history(self) -> list[TrinitySelfOptimizationReport]:
        return list(self._history)


def from_sara_system(system: Any, max_passes: int = 2) -> TrinitySelfOptimizer:
    components = system.components
    return TrinitySelfOptimizer(
        ara=components["ara_extended"],
        etr=components["etr_extended"],
        itr=components["itr_extended"],
        synergy=components.get("trinity") or components.get("trinity_eru"),
        max_passes=max_passes,
    )
