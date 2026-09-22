"""SARA — Núcleo: TrinitySynergy.

Orquestrador da autoaplicação da Trindade (ARA + ETR + ITR).
Une as versões estendidas em um ciclo convergente de autoaperfeiçoamento.

Fluxo:
  1. ARA detecta falhas (estruturais, relacionais, lexicais)
  2. ITR propõe plano estratégico
  3. ETR valida plano sob 4 frameworks
  4. ARA regenera
  5. ETR valida regeneração
  6. ITR executa
  7. Convergência quando todos aprovam

Aplica-se sobre qualquer alvo — inclusive sobre a própria Trindade.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sara.core.ara_extended import ARA_Extended
from sara.core.etr_extended import ETR_Extended
from sara.core.itr_extended import ITR_Extended
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.clock import now_iso
from sara.infra.hashing import hash_json
from sara.meta.eru_engine import ERU_Engine


@dataclass
class TrinityIteration:
    iteration: int
    ara_flaws: list[str]
    ara_structural: list[str]
    ara_relational: list[str]
    itr_plan_phases: int
    etr_consensus: float
    etr_dissenting: tuple[str, ...]
    regenerated: bool
    executed: bool
    converged: bool
    details: dict = field(default_factory=dict)


@dataclass
@dataclass(frozen=True)
class FusionMirror:
    cycle_id: str
    target: str
    ara: dict
    etr: dict
    itr: dict
    eru: dict
    fused_hash: str
    integrity_ok: bool = True


@dataclass
class TrinityReport:
    target: str
    iterations: list[TrinityIteration]
    final_text: str
    converged: bool
    total_iterations: int
    self_audit: dict = field(default_factory=dict)


class TrinitySynergy:
    """Orquestrador da autoaplicação da Trindade."""

    NAME = "TrinitySynergy"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.NUCLEAR
    DEPENDENCIES = ("ARA_Extended", "ETR_Extended", "ITR_Extended")
    CYCLE_PHASES = (
        CyclePhase.AUDIT, CyclePhase.REGENERATION,
        CyclePhase.ETHICS, CyclePhase.STRATEGY, CyclePhase.EXECUTION,
        CyclePhase.VALIDATION,
    )

    def __init__(self, ara: ARA_Extended, etr: ETR_Extended,
                 itr: ITR_Extended, max_iterations: int = 3,
                 eru: ERU_Engine | None = None) -> None:
        self._ara = ara
        self._etr = etr
        self._itr = itr
        self._eru = eru
        self._max_iterations = max_iterations
        self._mirrors: dict[str, FusionMirror] = {}

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "max_iterations": self._max_iterations,
            "fusion": {
                "aru_etr_itr": True,
                "eru_mirror": self._eru is not None,
                "mirrors": len(self._mirrors),
            },
        }

    def assess(self, target: str) -> dict:
        """Avalia a Tríade sobre um estado sem mutá-lo."""
        current = str(target)
        lexical = self._ara.detect(current)
        semantic = self._ara.detect_semantic(current)
        structural = self._ara.detect_structural(current)
        relational = self._ara.detect_relational(current)
        plan = self._itr.generate_strategic(current)
        ethical = self._etr.validate_multi_framework(current)
        return {
            "target_length": len(current),
            "flaws": {
                "lexical": [f.kind for f in lexical],
                "semantic": [f.kind for f in semantic],
                "structural": [f.kind for f in structural],
                "relational": [f.kind for f in relational],
            },
            "strategy": {
                "phases": len(plan.phases),
                "criteria": list(plan.convergence_criteria),
                "semantic_profile": self._itr.semantic_strategy_profile(current),
            },
            "ethics": {
                "approved": ethical.approved,
                "consensus": ethical.consensus_score,
                "dissenting": list(ethical.dissenting_frameworks),
            },
            "ready_for_regeneration": bool(
                lexical or semantic or structural or relational
            ),
        }

    def fuse_and_mirror(self, cycle_id: str, target: str,
                        ara_output: dict, etr_output: dict,
                        itr_output: dict) -> FusionMirror:
        """Funde os quatro estados sem substituir nenhum estado original.

        Cada subsistema mantém seu resultado próprio; o espelho é uma projeção
        imutável dos quatro resultados, com hash verificável. ERU congela cada
        estágio e o envelope final quando disponível.
        """
        if not cycle_id:
            raise ValueError("cycle_id é obrigatório")
        envelope = {
            "cycle_id": cycle_id,
            "target": str(target),
            "ara": dict(ara_output),
            "etr": dict(etr_output),
            "itr": dict(itr_output),
        }
        ara_hash = hash_json(envelope["ara"])
        etr_hash = hash_json(envelope["etr"])
        itr_hash = hash_json(envelope["itr"])
        eru_state = {
            "available": self._eru is not None,
            "ara_hash": ara_hash,
            "etr_hash": etr_hash,
            "itr_hash": itr_hash,
        }
        if self._eru is not None:
            eru_state["snapshot_hashes"] = {
                "ARA": self._eru.freeze(f"{cycle_id}:ARA", envelope["ara"]),
                "ETR": self._eru.freeze(f"{cycle_id}:ETR", envelope["etr"]),
                "ITR": self._eru.freeze(f"{cycle_id}:ITR", envelope["itr"]),
            }
        fused_hash = hash_json({**envelope, "eru": eru_state})
        if self._eru is not None:
            self._eru.freeze(f"{cycle_id}:FUSION", {**envelope, "eru": eru_state})
        mirror = FusionMirror(
            cycle_id=cycle_id,
            target=str(target),
            ara=envelope["ara"],
            etr=envelope["etr"],
            itr=envelope["itr"],
            eru=eru_state,
            fused_hash=fused_hash,
            integrity_ok=True,
        )
        self._mirrors[cycle_id] = mirror
        return mirror

    def mirror(self, cycle_id: str) -> FusionMirror | None:
        return self._mirrors.get(cycle_id)

    def audit_mirror(self, cycle_id: str) -> dict:
        mirror = self._mirrors.get(cycle_id)
        if mirror is None:
            return {"ok": False, "reason": "mirror_not_found"}
        payload = {
            "cycle_id": mirror.cycle_id,
            "target": mirror.target,
            "ara": mirror.ara,
            "etr": mirror.etr,
            "itr": mirror.itr,
            "eru": mirror.eru,
        }
        calculated = hash_json(payload)
        expected = hash_json(payload)
        return {
            "ok": calculated == expected == mirror.fused_hash,
            "fused_hash": mirror.fused_hash,
            "calculated_hash": calculated,
            "eru_available": bool(mirror.eru.get("available")),
        }

    # -----------------------------------------------------------------
    # Núcleo: ciclo de autoaplicação
    # -----------------------------------------------------------------

    def apply_to(self, target: str) -> TrinityReport:
        """Aplica a Trindade completa sobre o alvo."""
        current = str(target)
        iterations: list[TrinityIteration] = []

        for i in range(1, self._max_iterations + 1):
            # 1. ARA detecta (3 camadas)
            lexical_flaws = self._ara.detect(current)
            structural_flaws = self._ara.detect_structural(current)
            relational_flaws = self._ara.detect_relational(current)
            semantic_flaws = self._ara.detect_semantic(current)
            all_flaws = (
                list(lexical_flaws)
                + list(semantic_flaws)
                + list(relational_flaws)
                + list(structural_flaws)
            )

            # 2. ITR gera plano estratégico usando o estado auditado pelo ARA.
            ara_state = {
                "input": current,
                "flaws": [f.kind for f in all_flaws],
                "semantic_fingerprint": self._ara.analyze_semantics(current).fingerprint,
            }
            plan = self._itr.generate_strategic(
                current,
                context={"ara_audit": ara_state},
            )

            # 3. ETR valida o plano
            plan_text = f"{plan.objective} | phases={len(plan.phases)} | criteria={plan.convergence_criteria}"
            multi = self._etr.validate_multi_framework(plan_text)

            # 4. ARA regenera (se necessário)
            regenerated = False
            post_regeneration = None
            if all_flaws:
                regen = self._ara.regenerate_semantic(current, all_flaws)
                current = regen.transformed
                regenerated = True

            # 5. ETR valida o estado regenerado antes da execução estratégica.
            post_regeneration = self._etr.validate_multi_framework(current)

            # 6. ITR executa
            result = self._itr.execute_composed(plan, initial_text=current)
            current = result.transformed
            executed = not result.rollback_triggered

            # 7. ETR valida novamente o resultado da execução.
            post_execution = self._etr.validate_multi_framework(current)

            # 8. Espelhamento/fusão: nenhum subsistema perde seu estado próprio.
            mirror = self.fuse_and_mirror(
                cycle_id=f"trinity-{i}-{hash_json(current)[:12]}",
                target=current,
                ara_output={
                    "flaws": [f.kind for f in all_flaws],
                    "semantic_fingerprint": self._ara.analyze_semantics(current).fingerprint,
                },
                etr_output={
                    "pre_regeneration": multi.approved,
                    "post_regeneration": post_regeneration.approved,
                    "post_execution": post_execution.approved,
                    "consensus": post_execution.consensus_score,
                },
                itr_output={
                    "phases": len(plan.phases),
                    "rollback": result.rollback_triggered,
                    "metrics": result.metrics,
                    "fusion_hash": mirror.fused_hash,
                    "mirror_integrity": mirror.integrity_ok,
                },
            )

            # 9. Convergência
            converged = (
                not all_flaws
                and multi.approved
                and post_regeneration.approved
                and post_execution.approved
                and executed
            )

            iteration = TrinityIteration(
                iteration=i,
                ara_flaws=[f.kind for f in lexical_flaws],
                ara_structural=[f.kind for f in structural_flaws],
                ara_relational=[f.kind for f in relational_flaws],
                itr_plan_phases=len(plan.phases),
                etr_consensus=multi.consensus_score,
                etr_dissenting=multi.dissenting_frameworks,
                regenerated=regenerated,
                executed=executed,
                converged=converged,
                details={
                    "plan_criteria": list(plan.convergence_criteria),
                    "pre_regeneration_ethical": multi.approved,
                    "post_regeneration_ethical": post_regeneration.approved,
                    "post_execution_ethical": post_execution.approved,
                    "rollback_triggered": result.rollback_triggered,
                    "semantic_flaws": [f.kind for f in semantic_flaws],
                    "metrics": result.metrics,
                },
            )
            iterations.append(iteration)

            if converged:
                break

        # Relatório final
        return TrinityReport(
            target=str(target)[:200],
            iterations=iterations,
            final_text=current,
            converged=iterations[-1].converged if iterations else False,
            total_iterations=len(iterations),
        )

    # -----------------------------------------------------------------
    # Autoaplicação: Trindade sobre a Trindade
    # -----------------------------------------------------------------

    def apply_to_self(self) -> TrinityReport:
        """Aplica a Trindade sobre a própria Trindade."""
        self_repr = (
            f"TrinitySynergy v{self.VERSION} orquestrando "
            f"ARA_Extended + ETR_Extended + ITR_Extended. "
            f"Max iterations: {self._max_iterations}. "
            f"Frameworks: {list(self._etr.FRAMEWORKS)}. "
            f"Promove autonomia, transparência e cuidado com a comunidade."
        )
        report = self.apply_to(self_repr)
        # Adiciona meta-auditoria
        report.self_audit = {
            "ara_audit": self._ara.meta_audit_complete(),
            "ara_proposals": [
                {"rule": p.rule, "proposed": p.proposed_state}
                for p in self._ara.propose_rule_upgrade()
            ],
            "etr_upgrade_proposals": self._etr.propose_ethical_upgrade(),
            "itr_registry_optimization": {
                "new_steps": list(self._itr.optimize_registry().new_steps),
                "improvements": list(self._itr.optimize_registry().improvements),
            },
            "itr_trinity_proposals": self._itr.propose_trinity_evolution(),
        }
        return report
