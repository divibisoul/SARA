"""SARA — Meta: TransystemSARA.
Integração externa somente por endpoints explicitamente configurados.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
import os
import urllib.error
import urllib.request
from typing import Protocol
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase

@dataclass
class AssimilationReport:
    system: str
    component: str
    accepted: bool
    notes: str
    evidence: dict | None = None


class SystemAdapter(Protocol):
    def assimilate(self, component: str, constraints: list[str]) -> dict: ...


class HTTPSystemAdapter:
    """Adapter HTTP real para um endpoint explicitamente autorizado pelo operador."""

    def __init__(self, endpoint: str, token: str = "", timeout_s: float = 30.0) -> None:
        endpoint = endpoint.strip()
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError("endpoint deve ser http/https")
        self.endpoint = endpoint
        self.token = token
        self.timeout_s = timeout_s

    def assimilate(self, component: str, constraints: list[str]) -> dict:
        payload = json.dumps({
            "component": component,
            "constraints": list(constraints),
        }).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "SARA-Transystem/1.1",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(self.endpoint, data=payload, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(f"TRANSYSTEM_HTTP_{exc.code}:{detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"TRANSYSTEM_TRANSPORT_ERROR:{exc}") from exc
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("TRANSYSTEM_INVALID_JSON") from exc
        if not isinstance(result, dict):
            raise RuntimeError("TRANSYSTEM_INVALID_RESPONSE")
        return result


class TransystemSARA:
    NAME = "TransystemSARA"
    VERSION = "1.1"
    STATUS = ModuleStatus.PENDING_INFRASTRUCTURE
    ROLE = CycleRole.META
    DEPENDENCIES = ("QuantumCrawler", "NeuralLens", "NeuroIntegrator")
    CYCLE_PHASES = ()

    def __init__(self, adapters: dict[str, SystemAdapter] | None = None) -> None:
        self._adapters = dict(adapters or {})

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "credentials_ready": self.is_credentials_ready(),
            "configured_systems": sorted(self._adapters),
        }

    def is_credentials_ready(self) -> bool:
        return bool(self._adapters)

    def assimilate_from(self, system: str, component: str,
                        constraints: list[str]) -> AssimilationReport:
        name = str(system).strip()
        if not name:
            return AssimilationReport("", component, False, "system_required")
        adapter = self._adapters.get(name)
        if adapter is None:
            return AssimilationReport(
                name, component, False,
                "BLOCKED_INFRASTRUCTURE: sistema externo sem adapter explicitamente configurado",
                {"status": "BLOCKED_INFRASTRUCTURE"},
            )
        result = adapter.assimilate(component, constraints)
        accepted = bool(result.get("accepted", result.get("ok", False)))
        return AssimilationReport(
            name, component, accepted,
            "assimilação HTTP concluída" if accepted else "endpoint respondeu sem aceitar",
            {"status": "EXECUTED", "response": result},
        )

    def list_sources(self) -> list[str]:
        return ["NVIDIA", "Tesla", "Google", "OpenAI", "HuggingFace"]

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record(
                "governance", self.NAME, self.is_credentials_ready(),
                configured_systems=sorted(self._adapters),
            )

