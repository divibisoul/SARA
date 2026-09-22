from __future__ import annotations
import math
import statistics
from dataclasses import dataclass, field
from typing import Any, Protocol

from sara.omega.models import ETRContext, ETRMetric, ETRReport, ETRPlan, ETRAction, utc_now


class ETRNucleus(Protocol):
    id: str
    def analyze(self, context: ETRContext) -> ETRReport: ...


def _utilization_vector(context: ETRContext) -> list[float]:
    names = ("cpu_utilization", "memory_utilization", "disk_utilization")
    return [context.metric(n).value / 100.0 for n in names if context.metric(n) is not None]


class AnalysisNucleus:
    id = "ETR_AnalysisNucleus"
    def analyze(self, context: ETRContext) -> ETRReport:
        finite = [m for m in context.metrics if math.isfinite(m.value)]
        findings = tuple({
            "metric": m.name, "value": m.value, "unit": m.unit, "source": m.source
        } for m in finite)
        return ETRReport(self.id, bool(finite), findings, tuple(finite),
                         ("real_host_metrics",))


class AsymmetryNucleus:
    id = "ETR_AsymmetryNucleus"
    def analyze(self, context: ETRContext) -> ETRReport:
        values = _utilization_vector(context)
        if len(values) < 2:
            return ETRReport(self.id, True, (), evidence=("insufficient_comparable_metrics",))
        mean = statistics.fmean(values)
        mad = statistics.fmean(abs(v - mean) for v in values)
        coefficient = mad / mean if mean > 0 else 0.0
        finding = {"mean": mean, "mean_absolute_deviation": mad, "asymmetry": coefficient}
        return ETRReport(self.id, True, (finding,), evidence=("cpu_memory_disk_normalized",))


class EntropyNucleus:
    id = "ETR_EntropyNucleus"
    def analyze(self, context: ETRContext) -> ETRReport:
        values = _utilization_vector(context)
        if not values or sum(values) <= 0:
            return ETRReport(self.id, True, ({"entropy": 0.0},), evidence=("no_positive_distribution",))
        total = sum(values)
        probs = [v / total for v in values if v > 0]
        entropy = -sum(p * math.log(p, 2) for p in probs)
        maximum = math.log(len(probs), 2) if len(probs) > 1 else 1.0
        normalized = entropy / maximum if maximum else 0.0
        return ETRReport(self.id, True, ({"entropy_bits": entropy, "normalized_entropy": normalized},),
                         evidence=("shannon_over_normalized_resource_distribution",))


class RealityFilterNucleus:
    id = "ETR_RealityFilterNucleus"
    def analyze(self, context: ETRContext) -> ETRReport:
        findings = []
        for m in context.metrics:
            valid = math.isfinite(m.value)
            if m.unit == "%" and not 0 <= m.value <= 100:
                valid = False
            if not m.source or not m.observed_at:
                valid = False
            findings.append({"metric": m.name, "valid": valid, "source": m.source})
        return ETRReport(self.id, all(f["valid"] for f in findings), tuple(findings),
                         evidence=("finite_range_source_timestamp_validation",))


class SymbiosisHostNucleus:
    id = "ETR_SymbiosisHostNucleus"
    def plan(self, context: ETRContext, reports: tuple[ETRReport, ...]) -> ETRPlan:
        actions: list[ETRAction] = []
        reasons: list[str] = []
        memory = context.metric("memory_utilization")
        if memory and memory.value >= 85:
            # Não há ação host reversível comprovada para reduzir memória.
            # O sistema registra a condição e não fabrica uma otimização.
            reasons.append("memory_utilization_high:no_safe_reversible_host_action")
        cpu = context.metric("cpu_utilization")
        if cpu and cpu.value >= 90:
            reasons.append("cpu_utilization_high:no_safe_host_action_registered")
        return ETRPlan(
            plan_id=f"omega-plan-{context.cycle_id}",
            actions=tuple(actions),
            rationale=tuple(reasons) or ("no_safe_action_warranted",),
            generated_at=utc_now(),
        )

    @staticmethod
    def _gc_action() -> ETRAction:
        import gc
        before = {"collected": 0}
        def execute() -> dict[str, Any]:
            collected = gc.collect()
            before["collected"] = collected
            return {"action": "python_gc", "collected": collected}
        def rollback() -> dict[str, Any]:
            return {"action": "python_gc", "rollback": "not_applicable"}
        return ETRAction(
            "omega-gc", "python_gc", "Coletar lixo do processo SARA",
            # Python garbage collection is not reversible: collected objects cannot be restored by a rollback hook.
            impact=0.3, urgency=0.7, cost=0.05, reversible=False,
            execute=execute, rollback=rollback,
        )


class PrioritizationNucleus:
    id = "ETR_PrioritizationNucleus"
    def prioritize(self, plan: ETRPlan) -> ETRPlan:
        ordered = tuple(sorted(
            plan.actions,
            key=lambda a: (a.impact * a.urgency) / max(a.cost, 0.001),
            reverse=True,
        ))
        return ETRPlan(plan.plan_id, ordered, plan.rationale, plan.generated_at)


class ReverseExecutionNucleus:
    id = "ETR_ReverseExecutionNucleus"
    def execute(self, plan: ETRPlan) -> tuple:
        results = []
        for action in plan.actions:
            if not action.reversible:
                results.append({
                    "action_id": action.id, "ok": False,
                    "error": "NON_REVERSIBLE_ACTION_REJECTED",
                })
                continue
            try:
                output = action.execute()
                results.append({"action_id": action.id, "ok": True, "output": output})
            except Exception as exc:
                rollback_output = {}
                try:
                    rollback_output = action.rollback()
                except Exception as rb_exc:
                    rollback_output = {"error": f"{type(rb_exc).__name__}:{rb_exc}"}
                results.append({
                    "action_id": action.id, "ok": False,
                    "error": f"{type(exc).__name__}:{exc}",
                    "rollback": rollback_output,
                })
        return tuple(results)


@dataclass
class BanditArm:
    pulls: int = 0
    reward_sum: float = 0.0


class NeuralAdaptiveDirector:
    id = "ETR_NeuralAdaptiveDirector"
    def __init__(self, epsilon: float = 0.1) -> None:
        if not 0 <= epsilon <= 1:
            raise ValueError("epsilon deve estar entre 0 e 1")
        self.epsilon = epsilon
        self.arms: dict[str, BanditArm] = {"conservative": BanditArm(), "balanced": BanditArm()}

    def choose(self) -> str:
        import random
        if random.random() < self.epsilon:
            return random.choice(tuple(self.arms))
        return max(self.arms, key=lambda k: (
            self.arms[k].reward_sum / self.arms[k].pulls if self.arms[k].pulls else 0.0
        ))

    def update(self, arm: str, reward: float) -> dict[str, Any]:
        if arm not in self.arms:
            self.arms[arm] = BanditArm()
        reward = max(-1.0, min(1.0, float(reward)))
        state = self.arms[arm]
        state.pulls += 1
        state.reward_sum += reward
        return {"arm": arm, "pulls": state.pulls, "mean_reward": state.reward_sum / state.pulls}


class ETRGenesisSuite:
    NAME = "ETRGenesisSuite"
    VERSION = "1.0"
    NUCLEI = (
        AnalysisNucleus(), AsymmetryNucleus(), EntropyNucleus(),
        RealityFilterNucleus(),
    )

    def __init__(self) -> None:
        self.symbiosis = SymbiosisHostNucleus()
        self.prioritization = PrioritizationNucleus()
        self.reverse_execution = ReverseExecutionNucleus()
        self.adaptive = NeuralAdaptiveDirector()

    def analyze(self, context: ETRContext) -> tuple[ETRReport, ...]:
        return tuple(n.analyze(context) for n in self.NUCLEI)

    def build_plan(self, context: ETRContext, reports: tuple[ETRReport, ...]) -> ETRPlan:
        return self.prioritization.prioritize(self.symbiosis.plan(context, reports))

    def execute(self, plan: ETRPlan) -> tuple:
        return self.reverse_execution.execute(plan)
