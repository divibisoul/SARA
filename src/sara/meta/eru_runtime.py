"""Production-boundary composition for the ERU architecture.

This composes existing SARA modules instead of replacing them with a second
runtime. External Redis/Qdrant/DB transports remain explicit adapters.
"""
from __future__ import annotations
from typing import Any
from sara.infra.vagus_bus import VagusNerveBus
from sara.meta.bayesian_uncertainty import BayesianMetaLearner
from sara.memory.working_memory import WorkingMemory


class ERURuntime:
    NAME = "ERURuntime"
    VERSION = "1.0"

    def __init__(self, *, confidence_threshold: float = 0.85, vagus_bus: VagusNerveBus | None = None) -> None:
        self.bus = vagus_bus or VagusNerveBus()
        self.meta_learner = BayesianMetaLearner(confidence_threshold)
        self.working_memory = WorkingMemory()
        self._active = True

    async def assess_and_route(self, task: dict[str, Any]) -> dict[str, Any]:
        await self.bus.publish("USER_INTERFACE", "ERU_RUNTIME", "TASK_RECEIVED", task)
        readiness = self.meta_learner.evaluate(
            float(task.get("context_completeness", 0.0)),
            float(task.get("syntax_validity", 0.0)),
            float(task.get("historical_success_rate", 0.0)),
        )
        self.working_memory.put("last_readiness", readiness)
        if readiness["action_permitted"]:
            await self.bus.publish("ERU_RUNTIME", "SYSTEM", "EXECUTION_AUTHORIZED", readiness)
            return {"status": "AUTHORIZED", "readiness": readiness}
        await self.bus.publish(
            "ERU_RUNTIME", "MEMORY_ENGINE", "CONTEXT_FETCH_REQUEST",
            readiness, status="WAIT",
        )
        return {"status": "CONTEXT_REQUIRED", "readiness": readiness}

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "active": self._active,
            "bus": self.bus.describe(),
            "meta_learner": self.meta_learner.describe(),
            "working_memory": self.working_memory.describe(),
            "external_execution": False,
        }
