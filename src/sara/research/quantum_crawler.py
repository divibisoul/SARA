"""SARA — Pesquisa: QuantumCrawler.
Status: PENDING_INFRASTRUCTURE
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Optional
import json
import urllib.error
import urllib.request
import urllib.parse
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


class CrawlBackend(Protocol):
    def fetch(self, query: str) -> list[dict]: ...


@dataclass
class TechCandidate:
    source: str
    name: str
    license: str
    description: str




class HTTPJSONBackend:
    """Backend HTTP real configurável para APIs que devolvem JSON."""

    def __init__(self, endpoint_template: str, *,
                 token_env: str | None = None,
                 timeout_s: float = 20.0,
                 source: str = "HTTP") -> None:
        if "{query}" not in endpoint_template:
            raise ValueError("endpoint_template deve conter {query}")
        if timeout_s <= 0:
            raise ValueError("timeout_s deve ser positivo")
        self.endpoint_template = endpoint_template
        self.token_env = token_env
        self.timeout_s = timeout_s
        self.source = source

    def fetch(self, query: str) -> list[dict]:
        url = self.endpoint_template.format(
            query=urllib.parse.quote(str(query), safe="")
            if hasattr(urllib.request, "quote")
            else str(query)
        )
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "SARA-QuantumCrawler/1.0",
            },
        )
        if self.token_env:
            import os
            token = os.getenv(self.token_env, "").strip()
            if token:
                request.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(f"{self.source} HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"{self.source} backend failure: {exc}") from exc
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            if isinstance(payload.get("items"), list):
                return [item for item in payload["items"] if isinstance(item, dict)]
            if isinstance(payload.get("models"), list):
                return [item for item in payload["models"] if isinstance(item, dict)]
            return [payload]
        raise RuntimeError(f"{self.source} returned unsupported JSON shape")

class QuantumCrawler:
    NAME = "QuantumCrawler"
    VERSION = "1.0"
    STATUS = ModuleStatus.PENDING_INFRASTRUCTURE
    ROLE = CycleRole.RESEARCH
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.GOVERNANCE,)

    def __init__(self, backends: list[CrawlBackend]) -> None:
        self._backends = list(backends)

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "backends_configured": len(self._backends),
            "is_backends_ready": self.is_backends_ready(),
        }

    def is_backends_ready(self) -> bool:
        return len(self._backends) > 0

    def scan_configured(self, query: str) -> list[TechCandidate]:
        if not self._backends:
            raise NotImplementedError(
                "QuantumCrawler.scan_configured requer pelo menos um backend HTTP real."
            )
        candidates: list[TechCandidate] = []
        for backend in self._backends:
            for item in backend.fetch(query):
                candidates.append(
                    TechCandidate(
                        source=getattr(backend, "source", type(backend).__name__),
                        name=str(item.get("name") or item.get("id") or item.get("full_name") or ""),
                        license=str(item.get("license") or item.get("license_name") or ""),
                        description=str(item.get("description") or item.get("pipeline_tag") or ""),
                    )
                )
        return [c for c in candidates if c.name]

    def scan(self, query: str) -> list[TechCandidate]:
        raise NotImplementedError(
            "QuantumCrawler.scan requer backends reais de rede (GitHub API, "
            "HuggingFace API, arXiv API) com credenciais e rate limiting. "
            "Nenhum backend está configurado. "
            "Ativação: ver CANONICAL_ACTIVATION_PLAN.for_module('QuantumCrawler')."
        )

    def verify_source(self, candidate: TechCandidate) -> dict:
        raise NotImplementedError(
            "QuantumCrawler.verify_source requer acesso à rede para verificar "
            "autenticidade e licença da fonte. "
            "Ativação: ver CANONICAL_ACTIVATION_PLAN.for_module('QuantumCrawler')."
        )

    def list_sources(self) -> list[str]:
        return ["NVIDIA", "Tesla", "Google", "OpenAI", "HuggingFace"]

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, False,
                       reason="PENDING_INFRASTRUCTURE")