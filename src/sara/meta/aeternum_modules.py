"""AETERNUM 8-module bridge over the existing SARA authorities.

This adapter is an inventory/coordination layer. It does not introduce a second
event bus, memory engine, governance engine, ERU engine, or transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from sara.contracts.base import CyclePhase, CycleRole, ModuleStatus
from sara.contracts.registry import ModuleRegistry
from sara.meta.soul_federation import federation_manifest


@dataclass(frozen=True)
class AeternumBinding:
    module_id: str
    name: str
    owner: str
    local_authorities: tuple[str, ...]
    capabilities: tuple[str, ...]
    state_if_external: str = "federated_contract"

    def as_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "name": self.name,
            "owner": self.owner,
            "local_authorities": list(self.local_authorities),
            "capabilities": list(self.capabilities),
            "state_if_external": self.state_if_external,
        }


AETERNUM_8_BINDINGS: Final[tuple[AeternumBinding, ...]] = (
    AeternumBinding(
        "M1_CORE",
        "Núcleo Central",
        "N01",
        (),
        ("event-bus", "state-store", "registry", "neural-addressing"),
    ),
    AeternumBinding(
        "M2_ORCHESTRATION",
        "Orquestração",
        "N01",
        (),
        ("lifecycle", "routing-contract", "module-coordination"),
    ),
    AeternumBinding(
        "M3_LANGUAGE",
        "Córtex de Linguagem",
        "N05",
        (),
        ("conversation", "inference", "language"),
    ),
    AeternumBinding(
        "M4_MIND",
        "Consciência e Cognição",
        "N06",
        (),
        ("meta-cognition", "reasoning", "reflection"),
    ),
    AeternumBinding(
        "M5_PERCEPTION",
        "Percepção e Análise",
        "N03",
        (),
        ("audio", "speech", "multimodal"),
    ),
    AeternumBinding(
        "M6_IMMUNITY",
        "Autocorreção e Estabilidade",
        "N07_SARA",
        (
            "IdentityCore",
            "EmergencyRollback",
            "EthicalFilterChain",
            "InvariantValidator",
        ),
        ("audit", "invariants", "rollback", "ethical-validation"),
    ),
    AeternumBinding(
        "M7_EVOLUTION",
        "Evolução e Capacidades",
        "N07_SARA",
        (
            "ARAForge",
            "RegenerativeLoop",
            "InnovationRadar",
            "ProvenanceTracker",
        ),
        ("regeneration", "capability-governance", "provenance"),
    ),
    AeternumBinding(
        "M8_GOVERNANCE_MEMORY",
        "Governança e Memória",
        "N07_SARA",
        (
            "RegenerativeMemory",
            "TemporalVectorDB",
            "DecisionTrace",
            "GovernanceBackend",
            "ProvenanceTracker",
        ),
        ("long-term-memory", "governance", "trace", "provenance"),
    ),
)


class AeternumModuleAdapter:
    """Maps the eight AETERNUM domains onto already-registered SARA authorities."""

    NAME = "AeternumModuleAdapter"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = (
        "IdentityCore",
        "EmergencyRollback",
        "EthicalFilterChain",
        "ARAForge",
        "RegenerativeLoop",
        "InnovationRadar",
        "RegenerativeMemory",
        "TemporalVectorDB",
        "DecisionTrace",
        "GovernanceBackend",
        "ProvenanceTracker",
    )
    CYCLE_PHASES = (
        CyclePhase.PERSISTENCE,
        CyclePhase.SNAPSHOT,
        CyclePhase.MONITORING,
        CyclePhase.GOVERNANCE,
    )

    def __init__(self, registry: ModuleRegistry) -> None:
        self._registry = registry

    def describe(self) -> dict[str, Any]:
        validation = self.validate()
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "module_count": len(AETERNUM_8_BINDINGS),
            "registry_module_count": self._registry.snapshot()["count"],
            "validation_ok": validation["ok"],
            "non_destructive": True,
        }

    def bindings(self) -> list[dict[str, Any]]:
        return [binding.as_dict() for binding in AETERNUM_8_BINDINGS]

    def state_for(self, module_id: str) -> str:
        binding = next(
            (item for item in AETERNUM_8_BINDINGS if item.module_id == module_id),
            None,
        )
        if binding is None:
            raise KeyError(module_id)

        if not binding.local_authorities:
            return binding.state_if_external

        statuses = []
        for authority in binding.local_authorities:
            entry = self._registry.get(authority)
            if entry is None:
                return "in_progress"
            statuses.append(entry.status)

        if any(status == ModuleStatus.PENDING_INFRASTRUCTURE for status in statuses):
            return "pending_external_runtime"
        if all(status == ModuleStatus.IMPLEMENTED for status in statuses):
            return "implemented"
        return "in_progress"

    def validate(self) -> dict[str, Any]:
        missing: list[str] = []
        module_states: dict[str, str] = {}
        for binding in AETERNUM_8_BINDINGS:
            module_states[binding.module_id] = self.state_for(binding.module_id)
            for authority in binding.local_authorities:
                if self._registry.get(authority) is None:
                    missing.append(f"{binding.module_id} -> {authority}")

        return {
            "ok": not missing,
            "missing_local_authorities": missing,
            "module_states": module_states,
            "non_destructive": True,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "system": "AETERNUM↔SARA",
            "contract": "8-module-overlay/1.0",
            "bindings": self.bindings(),
            "validation": self.validate(),
            "sara_federation": federation_manifest(),
            "rule": "existing SARA authorities remain authoritative",
        }

    def emit_trace(self, ctx: Any) -> None:
        payload = self.snapshot()
        if hasattr(ctx, "record"):
            ctx.record(
                "meta",
                self.NAME,
                payload["validation"]["ok"],
                aeternum_module_count=len(AETERNUM_8_BINDINGS),
                non_destructive=True,
                module_states=payload["validation"]["module_states"],
            )
