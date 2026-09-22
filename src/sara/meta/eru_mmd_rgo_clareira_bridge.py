"""ERU ↔ MMD/RGO ↔ Trindade frontier bridge.

This adapter reconnects the previously independent ERU/MMD/RGO front with the
Clareira state stream without creating duplicate authorities.

- ERU remains the canonical reversible snapshot authority.
- MMD behavior is derived from ERU transition loss/change/addition sets.
- RGO behavior emits complementary capability proposals from material findings.
- The Trindade (ARA/ETR/ITR) assesses the structured evidence before proposal.
- No proposal is executed automatically.
"""
from __future__ import annotations

import copy
import json
import threading
from dataclasses import dataclass
from typing import Any

from sara.contracts.base import CyclePhase, CycleRole, ModuleStatus
from sara.core.provenance import Provenance
from sara.core.trinity_eru_unified import TrinityERUUnified
from sara.meta.clareira import ClareiraSubsystem
from sara.meta.eru_engine import ERU_Engine


RGO_FORMULA = "R(n+1)=F(T(I(A(O,C),C),C),C)"


@dataclass(frozen=True)
class FrontierAssessment:
    correlation_id: str
    status: str
    mmd: dict[str, Any]
    rgo: dict[str, Any]
    trinity: dict[str, Any]
    eru: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "status": self.status,
            "mmd": copy.deepcopy(self.mmd),
            "rgo": copy.deepcopy(self.rgo),
            "trinity": copy.deepcopy(self.trinity),
            "eru": copy.deepcopy(self.eru),
        }


class ERUMMDRGOClareiraBridge:
    """Cross-front adapter for ERU, MMD, RGO, Trindade and Clareira."""

    NAME = "ERUMMDRGOClareiraBridge"
    VERSION = "1.0.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = (
        "ERU_Engine",
        "ClareiraSubsystem",
        "TrinityERUUnified",
        "ProvenanceTracker",
    )
    CYCLE_PHASES = (
        CyclePhase.AUDIT,
        CyclePhase.STRATEGY,
        CyclePhase.VALIDATION,
        CyclePhase.PERSISTENCE,
    )

    def __init__(
        self,
        *,
        eru: ERU_Engine,
        clareira: ClareiraSubsystem,
        trinity: TrinityERUUnified,
        provenance: Any,
    ) -> None:
        self._eru = eru
        self._clareira = clareira
        self._trinity = trinity
        self._provenance = provenance
        self._history: list[FrontierAssessment] = []
        self._lock = threading.RLock()

    def describe(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.NAME,
                "version": self.VERSION,
                "status": self.STATUS.value,
                "role": self.ROLE.value,
                "dependencies": list(self.DEPENDENCIES),
                "phases": [p.value for p in self.CYCLE_PHASES],
                "history_count": len(self._history),
                "rgo_formula": RGO_FORMULA,
                "authority_boundary": {
                    "eru": "canonical_snapshot_recovery",
                    "mmd": "transition_missing_mass_derivation",
                    "rgo": "complementary_capability_proposal",
                    "trinity": "audit_strategy_validation",
                },
            }

    @staticmethod
    def _trinity_input(latest: dict[str, Any], diff: dict[str, Any]) -> str:
        payload = {
            "purpose": "auditoria estrutural do estado Clareira sem mutação",
            "preserve": True,
            "latest": {
                "schema_version": latest.get("schema_version"),
                "blueprint_version": latest.get("blueprint_version"),
                "node_count": latest.get("observed_node_count"),
                "channel_count": latest.get("observed_channel_count"),
                "homeostasis": latest.get("homeostasis"),
                "hash": latest.get("hash"),
            },
            "transition": {
                "lost": list(diff.get("lost", [])),
                "added": list(diff.get("added", [])),
                "changed": list(diff.get("changed", [])),
                "kept_count": len(diff.get("kept", [])),
            },
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _stable_diff(diff: Any) -> dict[str, Any]:
        """Normaliza DiffReport/dict e remove somente metadados de transporte."""
        volatile_roots = {"correlationId", "source", "timestamp"}
        if hasattr(diff, "__dict__"):
            raw = diff.__dict__
        elif isinstance(diff, dict):
            raw = diff
        else:
            raw = {}
        result: dict[str, Any] = {}
        for key in ("lost", "added", "changed", "kept"):
            values = raw.get(key, [])
            result[key] = [
                path for path in values
                if str(path).split(".", 1)[0] not in volatile_roots
            ]
        if "baseline" in raw:
            result["baseline"] = raw["baseline"]
        return result

    @staticmethod
    def _rgo_proposals(lost: list[str], changed: list[str]) -> list[dict[str, Any]]:
        findings = [
            ("MISSING", path, "RESTORE_OR_RETAIN")
            for path in lost
        ] + [
            ("CHANGED", path, "COMPARE_AND_PRESERVE")
            for path in changed
        ]
        proposals: list[dict[str, Any]] = []
        for kind, path, mechanism in findings:
            proposals.append({
                "finding_type": kind,
                "finding_path": path,
                "opposite_capability": mechanism,
                "tool_role": "recovery-and-preservation-adapter",
                "execution_status": "PROPOSED",
                "requires_validation": True,
                "requires_runtime_execution": True,
                "preservation": "original-retained",
            })
        return proposals

    def assess_latest(self, *, correlation_id: str) -> dict[str, Any]:
        if not correlation_id.strip():
            raise ValueError("CLAREIRA_FRONTIER_CORRELATION_REQUIRED")

        latest = self._clareira.latest_snapshot()
        if latest is None:
            raise ValueError("CLAREIRA_FRONTIER_NO_SNAPSHOT")

        history = self._clareira.snapshot_history(limit=2)
        current_name = str(latest.get("eru_snapshot_name", ""))
        older_name = ""
        if len(history) >= 2:
            older_name = str(history[-2].get("eru_snapshot_name", ""))

        raw_diff = (
            self._eru.compare(older_name, current_name)
            if older_name and current_name
            else {
                "lost": [],
                "added": [],
                "changed": [],
                "kept": [],
                "baseline": "NO_PREVIOUS_SNAPSHOT",
            }
        )
        diff = self._stable_diff(raw_diff)

        trinity = self._trinity.assess(self._trinity_input(latest, diff))
        lost = list(diff.get("lost", []))
        added = list(diff.get("added", []))
        changed = list(diff.get("changed", []))
        kept = list(diff.get("kept", []))
        proposals = self._rgo_proposals(lost, changed)

        assessment = FrontierAssessment(
            correlation_id=correlation_id,
            status="DERIVED",
            mmd={
                "status": "DERIVED",
                "source": "ERU.transition",
                "missing_mass": lost,
                "added_mass": added,
                "changed_mass": changed,
                "kept_mass": kept,
                "counts": {
                    "missing": len(lost),
                    "added": len(added),
                    "changed": len(changed),
                    "kept": len(kept),
                },
                "execution_status": "NOT_EXECUTED",
            },
            rgo={
                "status": "PROPOSED" if proposals else "NO_FINDING",
                "formula": RGO_FORMULA,
                "complementary_capabilities": proposals,
                "execution_status": "NOT_EXECUTED",
                "preservation": True,
            },
            trinity={
                "status": "OBSERVED",
                "assessment": trinity,
                "execution_status": "NOT_EXECUTED",
            },
            eru={
                "current_snapshot": current_name,
                "previous_snapshot": older_name or None,
                "transition_audited": bool(older_name),
                "functional_equivalence_proven": False,
            },
        )

        with self._lock:
            self._history.append(assessment)
            if len(self._history) > 128:
                del self._history[:-128]

        if self._provenance is not None:
            self._provenance.register(
                f"ERU.MMD.{correlation_id}",
                Provenance.RECONSTRUCTED,
                "Massa ausente/adicionada/alterada derivada de transição entre snapshots ERU de Clareira",
                source=self.NAME,
            )
            self._provenance.register(
                f"RGO.proposal.{correlation_id}",
                Provenance.INFERRED,
                "Capacidades complementares propostas a partir dos achados da transição; nenhuma execução implícita",
                source=self.NAME,
            )
            self._provenance.register(
                f"TRINITY.Clareira.{correlation_id}",
                Provenance.RECONSTRUCTED,
                "Avaliação ARA/ETR/ITR sobre evidência estrutural serializada do estado Clareira",
                source=self.NAME,
            )

        return assessment.as_dict()

    def latest_assessment(self) -> dict[str, Any] | None:
        with self._lock:
            return self._history[-1].as_dict() if self._history else None
