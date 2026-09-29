"""SARA — executable engineering gate for the integrated ARA/ETR/ITR/ERU runtime.

This module is observational: it audits the repository and the bootstrapped
runtime without mutating source modules. It never upgrades a blocked feature to
READY merely because a class or endpoint exists.
"""
from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REAL = "REAL"
PARTIAL = "PARTIAL"
BLOCKED = "BLOCKED"
UNMEASURABLE = "UNMEASURABLE"

# Historical inventory plus additions that are now first-class in the current
# SARA line. The gate detects accidental deletion, while new files are reported
# separately instead of being silently folded into history.
HISTORICAL_FILES = (
    "infra/hashing.py", "infra/clock.py", "infra/activation.py",
    "contracts/base.py", "contracts/context.py", "contracts/registry.py",
    "contracts/lifecycle.py", "contracts/activation.py", "contracts/invariants.py",
    "contracts/federation.py",
    "core/provenance.py", "core/ara.py", "core/ara_extended.py",
    "core/etr.py", "core/etr_extended.py", "core/itr.py", "core/itr_extended.py",
    "core/trinity_synergy.py", "core/trinity_eru_unified.py",
    "core/sistema_vivo.py", "core/connected_runtime.py",
    "memory/dna_tags.py", "memory/temporal_vector_db.py",
    "memory/regenerative_memory.py", "memory/working_memory.py",
    "security/identity_core.py", "security/emergency_rollback.py",
    "security/ethical_filter_chain.py", "security/safe_sandbox.py",
    "regeneration/regenerative_loop.py", "regeneration/regenerative_state.py",
    "regeneration/synergy_engine.py",
    "monitoring/storm_monitor.py", "monitoring/decision_trace.py",
    "monitoring/governance.py", "monitoring/execution_report.py",
    "research/quantum_crawler.py", "research/neural_lens.py",
    "research/innovation_radar.py", "research/neuro_integrator.py",
    "research/quantum_scanner.py",
    "governance/ubuntu_ethics.py", "governance/buen_vivir.py",
    "governance/legal_ai.py", "governance/legal_compliance.py",
    "governance/governed_sara.py",
    "meta/ara_forge.py", "meta/assimilation_committee.py",
    "meta/quantum_snapshot.py", "meta/eru_engine.py",
    "meta/eru_trinity_bridge.py", "meta/eru_drift_detector.py",
    "meta/eru_recovery_advisor.py", "meta/eru_runtime.py",
    "meta/transystem_sara.py", "meta/aeternum_chimera.py",
    "omega/models.py", "omega/scanner.py", "omega/nuclei.py",
    "omega/soul_services.py", "omega/hal.py", "omega/security.py",
    "omega/system.py", "omega/__init__.py",
    "audit/cycle_auditor.py",
)

REQUIRED_SYMBOLS = {
    "core/ara_extended.py": (
        "detect_structural", "detect_relational", "detect_semantic",
        "regenerate_semantic", "meta_audit_complete", "propose_rule_upgrade",
        "applied_to_self",
    ),
    "core/etr_extended.py": (
        "validate_multi_framework", "validate_against_self",
        "validate_trinity", "explain_decision", "propose_ethical_upgrade",
    ),
    "core/itr_extended.py": (
        "generate_strategic", "execute_composed", "analyze_patterns",
        "optimize_registry", "propose_trinity_evolution",
    ),
    "core/trinity_synergy.py": (
        "assess", "fuse_and_mirror", "mirror", "audit_mirror",
        "apply_to", "apply_to_self",
    ),
    "core/trinity_eru_unified.py": (
        "assess", "apply_to", "audit_cycle", "recovery_advice",
        "fuse_and_mirror", "mirror", "audit_mirror",
    ),
    "meta/eru_engine.py": (
        "freeze", "checkpoint", "compare", "recover",
        "detect_information_loss", "reconstructability",
    ),
    "meta/eru_trinity_bridge.py": (
        "observe", "observe_capabilities", "record_behavior",
        "detect_drift", "advise_recovery", "audit_cycle",
    ),
    "regeneration/regenerative_loop.py": (
        "run", "_phase_ingestion", "_phase_audit", "_phase_regeneration",
        "_phase_identity", "_phase_ethics", "_phase_strategy",
        "_phase_execution", "_phase_validation", "_phase_persistence",
        "_phase_snapshot", "_phase_monitoring", "_phase_governance",
    ),
}

EXTERNAL_BLOCKED = {
    "security/safe_sandbox.py": "real isolation backend",
    "research/quantum_crawler.py": "real network crawler backends",
    "research/quantum_scanner.py": "real target/toolchain access",
    "governance/legal_ai.py": "real patent oracle",
    "monitoring/decision_trace.py": "real IPFS node/gateway for external publication",
    "meta/transystem_sara.py": "real external system adapters/credentials",
}


@dataclass(frozen=True)
class GateItem:
    item: str
    status: str
    evidence: str


@dataclass(frozen=True)
class EngineeringGateReport:
    status: str
    critical_ok: bool
    inventory: dict[str, Any]
    items: tuple[GateItem, ...]
    blockers: tuple[str, ...]
    findings: tuple[str, ...]
    integrity_hash: str


class EngineeringGate:
    """Conservative audit that treats implementation and evidence separately."""

    def __init__(self, package_root: str | Path | None = None) -> None:
        self.package_root = Path(package_root or Path(__file__).resolve().parents[1])

    def _python_files(self) -> list[Path]:
        return sorted(self.package_root.rglob("*.py"))

    @staticmethod
    def _parse(path: Path) -> ast.AST | None:
        try:
            return ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            return None

    def inventory(self) -> dict[str, Any]:
        files = self._python_files()
        current = {str(p.relative_to(self.package_root)) for p in files}
        missing = sorted(set(HISTORICAL_FILES) - current)
        invalid: list[str] = []
        classes: list[str] = []
        functions: list[str] = []
        imports: list[str] = []
        dependencies: dict[str, list[str]] = {}

        for path in files:
            rel = str(path.relative_to(self.package_root))
            tree = self._parse(path)
            if tree is None:
                invalid.append(rel)
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(f"{rel}:{node.name}")
                    for stmt in node.body:
                        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                            targets = []
                            if isinstance(stmt, ast.Assign):
                                targets = [t for t in stmt.targets if isinstance(t, ast.Name)]
                            elif isinstance(stmt.target, ast.Name):
                                targets = [stmt.target]
                            for target in targets:
                                if target.id != "DEPENDENCIES":
                                    continue
                                try:
                                    value = stmt.value
                                    dependencies[f"{rel}:{node.name}"] = list(ast.literal_eval(value))
                                except (ValueError, TypeError):
                                    dependencies[f"{rel}:{node.name}"] = ["UNMEASURABLE"]
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append(f"{rel}:{node.name}")
                elif isinstance(node, ast.Import):
                    imports.extend(f"{rel}:{a.name}" for a in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(f"{rel}:{node.module or ''}")

        return {
            "python_files": len(files),
            "classes": len(classes),
            "functions": len(functions),
            "imports": len(imports),
            "historical_expected": len(HISTORICAL_FILES),
            "historical_missing": missing,
            "syntax_invalid": sorted(invalid),
            "current_only_files": sorted(current - set(HISTORICAL_FILES)),
            "declared_dependencies": dependencies,
        }

    def _hazards(self) -> dict[str, list[str]]:
        result = {"pass": [], "todo_fixme": [], "not_implemented": [], "mock_stub_fake_dummy": []}
        for path in self._python_files():
            rel = str(path.relative_to(self.package_root))
            raw = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(raw.splitlines(), 1):
                upper = line.upper()
                unfinished_tokens = ("TO" + "DO", "FIX" + "ME")
                if any(token in upper for token in unfinished_tokens):
                    result["todo_fixme"].append(f"{rel}:{lineno}")
                if "NOTIMPLEMENTEDERROR" in upper:
                    result["not_implemented"].append(f"{rel}:{lineno}")
                if any(token in upper for token in ("MOCK", "STUB", "FAKE", "DUMMY")):
                    result["mock_stub_fake_dummy"].append(f"{rel}:{lineno}")
            tree = self._parse(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Pass):
                    result["pass"].append(f"{rel}:{getattr(node, 'lineno', '?')}")
        return result

    @staticmethod
    def _find_symbols(path: Path) -> set[str]:
        tree = EngineeringGate._parse(path)
        if tree is None:
            return set()
        return {
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def _runtime_probe(self) -> dict[str, Any]:
        try:
            from sara.bootstrap import build_default_system
            system = build_default_system(fail_closed=True)
            required_components = {
                "ara_extended", "etr_extended", "itr_extended",
                "eru", "eru_bridge", "trinity_eru", "working_memory",
                "omega", "aeternum_chimera", "connected_runtime",
            }
            missing = sorted(required_components - set(system.components))
            dependency_order = system.registry.dependency_order()
            return {
                "status": REAL if system.ready and not missing else PARTIAL,
                "ready": bool(system.ready),
                "missing_components": missing,
                "dependency_order_count": len(dependency_order),
                "invariants": system.invariant_report,
                "registration": system.registration_report,
            }
        except Exception as exc:
            return {
                "status": UNMEASURABLE,
                "ready": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    def audit(self) -> EngineeringGateReport:
        inv = self.inventory()
        hazards = self._hazards()
        items: list[GateItem] = []
        blockers: list[str] = []
        findings: list[str] = []

        if inv["historical_missing"]:
            items.append(GateItem("historical_inventory", UNMEASURABLE, ";".join(inv["historical_missing"])))
            blockers.extend(inv["historical_missing"])
        else:
            items.append(GateItem("historical_inventory", REAL, f"{len(HISTORICAL_FILES)} historical files present"))

        if inv["syntax_invalid"]:
            items.append(GateItem("syntax_integrity", UNMEASURABLE, ";".join(inv["syntax_invalid"])))
            blockers.extend(inv["syntax_invalid"])
        else:
            items.append(GateItem("syntax_integrity", REAL, f"{inv['python_files']} Python files parse"))

        for rel, required in REQUIRED_SYMBOLS.items():
            path = self.package_root / rel
            missing = sorted(set(required) - self._find_symbols(path)) if path.exists() else list(required)
            status = REAL if not missing else UNMEASURABLE
            items.append(GateItem(f"required_symbols::{rel}", status, "ok" if not missing else ",".join(missing)))
            if missing:
                blockers.append(f"{rel}:{','.join(missing)}")

        runtime = self._runtime_probe()
        items.append(GateItem("bootstrap_runtime", runtime["status"], json.dumps(
            {k: runtime[k] for k in runtime if k != "invariants" and k != "registration"},
            ensure_ascii=False,
            sort_keys=True,
        )))
        if runtime["status"] == UNMEASURABLE:
            blockers.append("bootstrap_runtime")

        for rel, reason in EXTERNAL_BLOCKED.items():
            path = self.package_root / rel
            status = BLOCKED if path.exists() and "NotImplementedError" in path.read_text(encoding="utf-8") else PARTIAL
            items.append(GateItem(f"external::{rel}", status, reason))

        for name, values in hazards.items():
            if values:
                findings.append(f"{name}={len(values)}")
        items.append(GateItem("anti_simulation_static_scan", PARTIAL if hazards["mock_stub_fake_dummy"] else REAL,
                              json.dumps({k: len(v) for k, v in hazards.items()}, sort_keys=True)))

        # The static report is deliberately conservative: a passing runtime
        # probe does not erase explicit external BLOCKED states or the static
        # findings that require human/code-level interpretation.
        critical_ok = not blockers
        status = REAL if critical_ok and not any(i.status == PARTIAL for i in items) else PARTIAL
        if not critical_ok:
            status = UNMEASURABLE

        payload = {
            "status": status,
            "critical_ok": critical_ok,
            "inventory": inv,
            "items": [asdict(i) for i in items],
            "blockers": blockers,
            "findings": findings,
        }
        integrity_hash = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

        return EngineeringGateReport(
            status=status,
            critical_ok=critical_ok,
            inventory=inv,
            items=tuple(items),
            blockers=tuple(blockers),
            findings=tuple(findings),
            integrity_hash=integrity_hash,
        )

    @classmethod
    def run(cls, package_root: str | Path | None = None) -> dict[str, Any]:
        report = cls(package_root).audit()
        return {
            "status": report.status,
            "critical_ok": report.critical_ok,
            "inventory": report.inventory,
            "items": [asdict(i) for i in report.items],
            "blockers": list(report.blockers),
            "findings": list(report.findings),
            "integrity_hash": report.integrity_hash,
        }


if __name__ == "__main__":
    print(json.dumps(EngineeringGate.run(), ensure_ascii=False, indent=2, sort_keys=True))
