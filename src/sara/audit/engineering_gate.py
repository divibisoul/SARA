"""SARA — engineering gate: executable completeness and anti-false-green audit.

The gate is intentionally additive. It does not mutate the runtime; it reports
what the repository can prove about itself and distinguishes REAL, PARTIAL,
BLOCKED and UNMEASURABLE states.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


REAL = "REAL"
PARTIAL = "PARTIAL"
BLOCKED = "BLOCKED"
UNMEASURABLE = "UNMEASURABLE"

HISTORICAL_PY_FILES = (
    "infra/hashing.py", "infra/clock.py",
    "contracts/base.py", "contracts/context.py", "contracts/registry.py",
    "contracts/lifecycle.py", "contracts/activation.py", "contracts/invariants.py",
    "core/provenance.py", "core/ara.py", "core/ara_extended.py",
    "core/etr.py", "core/etr_extended.py", "core/itr.py", "core/itr_extended.py",
    "core/trinity_synergy.py", "core/sistema_vivo.py", "core/connected_runtime.py",
    "memory/dna_tags.py", "memory/temporal_vector_db.py",
    "memory/regenerative_memory.py",
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
    "meta/quantum_snapshot.py", "meta/eru_engine.py", "meta/transystem_sara.py",
    "audit/cycle_auditor.py",
)

EXTERNAL_BLOCKED_FILES = {
    "security/safe_sandbox.py",
    "research/quantum_crawler.py",
    "research/quantum_scanner.py",
    "governance/legal_ai.py",
    "monitoring/decision_trace.py",
    "meta/transystem_sara.py",
}

@dataclass(frozen=True)
class GateItem:
    item: str
    status: str
    evidence: str = ""

@dataclass(frozen=True)
class EngineeringGateReport:
    status: str
    critical_ok: bool
    inventory: dict
    items: tuple[GateItem, ...]
    blockers: tuple[str, ...]
    findings: tuple[str, ...]
    integrity_hash: str


class EngineeringGate:
    """Audit repository state with executable, conservative classifications."""

    def __init__(self, source_root: str | Path | None = None) -> None:
        self.source_root = Path(source_root or Path(__file__).resolve().parents[1])

    def _python_files(self) -> list[Path]:
        return sorted(self.source_root.rglob("*.py"))

    @staticmethod
    def _ast(path: Path) -> ast.AST | None:
        try:
            return ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            return None

    def inventory(self) -> dict:
        files = self._python_files()
        classes: list[str] = []
        functions: list[str] = []
        imports: list[str] = []
        dependencies: dict[str, list[str]] = {}
        invalid: list[str] = []

        for path in files:
            tree = self._ast(path)
            rel = str(path.relative_to(self.source_root))
            if tree is None:
                invalid.append(rel)
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append(f"{rel}:{node.name}")
                elif isinstance(node, ast.ClassDef):
                    classes.append(f"{rel}:{node.name}")
                    for stmt in node.body:
                        if isinstance(stmt, ast.Assign):
                            for target in stmt.targets:
                                if isinstance(target, ast.Name) and target.id == "DEPENDENCIES":
                                    try:
                                        value = ast.literal_eval(stmt.value)
                                        dependencies[f"{rel}:{node.name}"] = list(value)
                                    except (ValueError, TypeError):
                                        dependencies[f"{rel}:{node.name}"] = ["UNMEASURABLE"]
                elif isinstance(node, ast.Import):
                    imports.extend(f"{rel}:{alias.name}" for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(f"{rel}:{node.module or ''}")

        historical = [f"src/sara/{item}" for item in HISTORICAL_PY_FILES]
        current = {str(p.relative_to(self.source_root)) for p in files}
        missing = [p for p in historical if p not in {f"src/sara/{x}" for x in current}]

        return {
            "python_files": len(files),
            "classes": len(classes),
            "functions": len(functions),
            "imports": len(imports),
            "declared_dependencies": dependencies,
            "historical_expected_files": len(HISTORICAL_PY_FILES),
            "historical_missing": missing,
            "syntax_invalid": invalid,
        }

    def _scan_hazards(self) -> tuple[list[str], list[str], list[str]]:
        pass_hits: list[str] = []
        todo_hits: list[str] = []
        forbidden_hits: list[str] = []

        for path in self._python_files():
            rel = str(path.relative_to(self.source_root))
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines()
            for lineno, line in enumerate(lines, 1):
                upper = line.upper()
                if "TODO" in upper or "FIXME" in upper:
                    todo_hits.append(f"{rel}:{lineno}")
                if "MOCK" in upper or "STUB" in upper or "FAKE" in upper or "DUMMY" in upper:
                    forbidden_hits.append(f"{rel}:{lineno}:{line.strip()[:120]}")

            tree = self._ast(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Pass):
                    pass_hits.append(f"{rel}:{getattr(node, 'lineno', '?')}")

        return pass_hits, todo_hits, forbidden_hits

    def _classify_external_blockers(self) -> list[GateItem]:
        items: list[GateItem] = []
        for rel in sorted(EXTERNAL_BLOCKED_FILES):
            path = self.source_root / rel
            if not path.exists():
                items.append(GateItem(rel, UNMEASURABLE, "arquivo ausente"))
                continue
            text = path.read_text(encoding="utf-8")
            if "NotImplementedError" in text:
                items.append(GateItem(rel, BLOCKED, "infraestrutura externa explicitamente requerida"))
            else:
                items.append(GateItem(rel, PARTIAL, "depende de infraestrutura externa; sem marcador explícito"))
        return items

    def _hash(self, payload: object) -> str:
        import hashlib
        import json
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def audit(self) -> EngineeringGateReport:
        inv = self.inventory()
        pass_hits, todo_hits, forbidden_hits = self._scan_hazards()
        items: list[GateItem] = []
        findings: list[str] = []
        blockers: list[str] = []

        missing = inv["historical_missing"]
        if missing:
            items.append(GateItem("historical_inventory", UNMEASURABLE, ";".join(missing)))
            blockers.extend(missing)
        else:
            items.append(GateItem("historical_inventory", REAL, f"{inv['historical_expected_files']} expected files present"))

        if inv["syntax_invalid"]:
            items.append(GateItem("syntax_integrity", UNMEASURABLE, ";".join(inv["syntax_invalid"])))
            blockers.extend(inv["syntax_invalid"])
        else:
            items.append(GateItem("syntax_integrity", REAL, f"{inv['python_files']} Python files parsed"))

        if todo_hits:
            findings.append(f"TODO/FIXME occurrences: {len(todo_hits)}")
        items.append(GateItem("todo_scan", PARTIAL if todo_hits else REAL, f"count={len(todo_hits)}"))

        if pass_hits:
            findings.append(f"pass statements: {len(pass_hits)}")
        items.append(GateItem("pass_scan", PARTIAL if pass_hits else REAL, f"count={len(pass_hits)}"))

        if forbidden_hits:
            # 'mock/stub/fake/dummy' is a finding, not automatically a failure:
            # source comments and compatibility helpers must be examined by scope.
            findings.append(f"mock/stub/fake/dummy textual hits: {len(forbidden_hits)}")
        items.append(GateItem("anti_simulation_scan", PARTIAL if forbidden_hits else REAL, f"count={len(forbidden_hits)}"))

        external = self._classify_external_blockers()
        items.extend(external)
        blockers.extend(i.item for i in external if i.status == UNMEASURABLE)

        critical_ok = not blockers and not inv["syntax_invalid"] and not missing
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
        return EngineeringGateReport(
            status=status,
            critical_ok=critical_ok,
            inventory=inv,
            items=tuple(items),
            blockers=tuple(blockers),
            findings=tuple(findings),
            integrity_hash=self._hash(payload),
        )

    @classmethod
    def run(cls, source_root: str | Path | None = None) -> dict:
        report = cls(source_root).audit()
        return {
            "status": report.status,
            "critical_ok": report.critical_ok,
            "inventory": report.inventory,
            "items": [asdict(item) for item in report.items],
            "blockers": list(report.blockers),
            "findings": list(report.findings),
            "integrity_hash": report.integrity_hash,
        }


if __name__ == "__main__":
    import json
    print(json.dumps(EngineeringGate.run(), ensure_ascii=False, indent=2, sort_keys=True))
