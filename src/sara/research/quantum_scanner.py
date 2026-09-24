"""SARA — Pesquisa: QuantumScanner.
Status: PENDING_INFRASTRUCTURE
"""
from __future__ import annotations
from typing import Literal
import ast
import hashlib
import pathlib
import shutil
import subprocess
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


class QuantumScanner:
    NAME = "QuantumScanner"
    VERSION = "1.1"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.RESEARCH
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.GOVERNANCE,)

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "local_scan_ready": True,
            "file_probe_ready": shutil.which("file") is not None,
            "objdump_ready": shutil.which("objdump") is not None,
        }

    def is_target_access_ready(self, target: str | None = None) -> bool:
        if target is None:
            return True
        return pathlib.Path(target).is_file()

    def scan_source_file(self, target: str) -> dict:
        path = pathlib.Path(target)
        if not path.is_file():
            raise FileNotFoundError(f"target não encontrado: {target}")
        source = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        suffix = path.suffix.lower()
        result = {
            "target": str(path),
            "sha256": digest,
            "bytes": len(source.encode("utf-8")),
            "lines": len(source.splitlines()),
            "language": suffix,
            "functions": [],
            "classes": [],
            "imports": [],
            "syntax_valid": True,
            "findings": [],
        }
        if suffix == ".py":
            try:
                tree = ast.parse(source, filename=str(path))
            except SyntaxError as exc:
                result["syntax_valid"] = False
                result["findings"].append({
                    "kind": "syntax_error",
                    "line": exc.lineno,
                    "message": exc.msg,
                })
                return result
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    result["functions"].append(node.name)
                elif isinstance(node, ast.ClassDef):
                    result["classes"].append(node.name)
                elif isinstance(node, ast.Import):
                    result["imports"].extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    result["imports"].append(node.module)
            return result
        result["findings"].append({
            "kind": "language_not_parser_supported",
            "message": "scanner local exige parser específico para análise estrutural desta linguagem",
        })
        return result

    def scan(self, target: str,
             depth: Literal["shallow", "deep", "atomic"] = "shallow") -> dict:
        if depth not in {"shallow", "deep", "atomic"}:
            raise ValueError("depth inválido")
        path = pathlib.Path(str(target))
        if path.is_file() and path.suffix.lower() == ".py":
            result = self.scan_source_file(str(path))
            result["depth"] = depth
            result["backend"] = "local_source_parser"
            return result
        if path.is_file():
            result = {
                "target": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
                "lines": len(path.read_text(encoding="utf-8", errors="replace").splitlines()),
                "language": path.suffix.lower(),
                "functions": [],
                "classes": [],
                "imports": [],
                "syntax_valid": True,
                "findings": [],
                "depth": depth,
                "backend": "file"
            }
            file_probe = subprocess.run(
                ["file", "-b", str(path)],
                check=False, capture_output=True, text=True, timeout=5,
            )
            result["file_type"] = file_probe.stdout.strip()
            if file_probe.returncode != 0:
                result["findings"].append({"kind": "file_probe_failed", "message": file_probe.stderr.strip()})
            objdump = shutil.which("objdump")
            if depth in {"deep", "atomic"} and objdump:
                header_probe = subprocess.run(
                    [objdump, "-f", str(path)],
                    check=False, capture_output=True, text=True, timeout=10,
                )
                result["objdump"] = header_probe.stdout.strip()
                if header_probe.returncode != 0:
                    result["findings"].append({"kind": "objdump_failed", "message": header_probe.stderr.strip()})
            elif depth in {"deep", "atomic"}:
                result["findings"].append({
                    "kind": "deep_disassembler_unavailable",
                    "message": "objdump não encontrado; análise de formato permanece disponível via file",
                })
            return result
        raise FileNotFoundError(f"target não encontrado: {target}")

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, True,
                       local_scan_ready=True,
                       file_probe_ready=shutil.which("file") is not None,
                       objdump_ready=shutil.which("objdump") is not None)