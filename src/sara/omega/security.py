from __future__ import annotations
from dataclasses import dataclass
import os
from typing import Any

from sara.security.safe_sandbox import SafeSandbox


class CodeValidator:
    NAME = "OmegaCodeValidator"

    def __init__(self, sandbox: SafeSandbox) -> None:
        self._sandbox = sandbox

    def validate(self, code: str) -> dict[str, Any]:
        result = self._sandbox.analyze_static(code)
        return {
            "approved": result.parsed and not result.vulnerabilities,
            "parsed": result.parsed,
            "nodes": result.nodes,
            "vulnerabilities": list(result.vulnerabilities),
        }


@dataclass(frozen=True)
class PermissionState:
    name: str
    available: bool
    source: str


class PermissionManager:
    NAME = "OmegaPermissionManager"

    def inspect(self) -> tuple[PermissionState, ...]:
        return (
            PermissionState("docker", self._command_exists("docker"), "host"),
            PermissionState("shizuku", False, "not_available_in_python_runtime"),
            PermissionState("root", os.geteuid() == 0 if hasattr(os, "geteuid") else False, "host"),
        )

    @staticmethod
    def _command_exists(command: str) -> bool:
        import shutil
        return shutil.which(command) is not None


class AuditLog:
    NAME = "OmegaAuditLog"

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    def append(self, event: str, **data: Any) -> dict[str, Any]:
        entry = {"event": str(event), **data}
        self._entries.append(entry)
        return dict(entry)

    def entries(self) -> list[dict[str, Any]]:
        return [dict(e) for e in self._entries]
