"""SARA G0 kernel adapter for the Octacore system processor.

This class exposes existing SARA authorities as kernel operations. It does not
reimplement ARA/ETR/ITR or create a second regeneration engine.
"""
from __future__ import annotations
from typing import Any

from sara.contracts.base import CyclePhase, CycleRole, ModuleStatus


class OctaCoreG0Kernel:
    NAME = "OctaCoreG0Kernel"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = ("RegenerativeLoop", "SistemaVivo", "ARA_Extended", "ETR_Extended", "DecisionTrace")
    CYCLE_PHASES = tuple(CyclePhase)
    KERNEL_ID = "G0"
    NUCLEUS = "SARA"
    CAPABILITIES = ("sara.cycle", "sara.audit", "sara.regenerate", "sara.state", "sara.trace")

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "slot": self.KERNEL_ID,
            "nucleus": self.NUCLEUS,
            "type": "system_gpu_regenerative_kernel",
            "silicon_gpu": False,
            "authoritative": True,
            "capabilities": list(self.CAPABILITIES),
            "delegation": "existing SARA HTTP/runtime contracts",
        }

    def cycle(self, sistema_vivo: Any, input_text: str, *, cycle_id: str | None = None, context: dict[str, Any] | None = None) -> Any:
        return sistema_vivo.process(input_text, cycle_id=cycle_id, context=context)

    def audit(self, ara_extended: Any, etr_extended: Any, input_text: str) -> dict[str, Any]:
        flaws = [
            *ara_extended.detect(input_text),
            *getattr(ara_extended, "detect_semantic", lambda _t: [])(input_text),
            *getattr(ara_extended, "detect_structural", lambda _t: [])(input_text),
            *getattr(ara_extended, "detect_relational", lambda _t: [])(input_text),
        ]
        ethical = etr_extended.validate_multi_framework(input_text)
        return {
            "operation": "audit",
            "flaws": [getattr(item, "__dict__", str(item)) for item in flaws],
            "count": len(flaws),
            "ethical": getattr(ethical, "__dict__", str(ethical)),
        }

    def regenerate(self, ara_extended: Any, etr_extended: Any, input_text: str) -> dict[str, Any]:
        flaws = [
            *ara_extended.detect(input_text),
            *getattr(ara_extended, "detect_semantic", lambda _t: [])(input_text),
            *getattr(ara_extended, "detect_structural", lambda _t: [])(input_text),
            *getattr(ara_extended, "detect_relational", lambda _t: [])(input_text),
        ]
        regenerated = ara_extended.regenerate_semantic(input_text, flaws)
        ethical = etr_extended.validate_multi_framework(regenerated.transformed)
        return {
            "operation": "regenerate",
            "original": regenerated.original,
            "transformed": regenerated.transformed,
            "applied_rules": list(regenerated.applied_rules),
            "plan_steps": list(regenerated.plan_steps),
            "integrity_hash": regenerated.integrity_hash,
            "ethical": getattr(ethical, "__dict__", str(ethical)),
        }

    def state(self, sistema_vivo: Any) -> dict[str, Any]:
        return sistema_vivo.state()

    def trace(self, trace: Any, cycle_id: str) -> dict[str, Any]:
        entries = trace.query({"cycle_id": cycle_id})
        return {
            "cycle_id": cycle_id,
            "integrity": trace.verify(),
            "entries": [getattr(entry, "__dict__", str(entry)) for entry in entries],
        }
