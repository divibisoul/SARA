"""SARA — Meta: ARAForge.
Status: IMPLEMENTED
"""
from __future__ import annotations
from dataclasses import dataclass
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


@dataclass
class AdaptedManifest:
    name: str
    original_prompt: str
    adapted_prompt: str
    constraints: tuple[str, ...]


class ARAForge:
    NAME = "ARAForge"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.GOVERNANCE,)

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
        }

    def adapt(self, manifest: dict, constraints: list[str]) -> AdaptedManifest:
        base = manifest.get("core_functionality_prompt", "")
        suffix = "\nRestrições Estritas:\n" + "\n".join(f"- {c}" for c in constraints)
        return AdaptedManifest(
            name=manifest.get("name", "unknown"),
            original_prompt=base,
            adapted_prompt=base + suffix,
            constraints=tuple(constraints),
        )

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, True)