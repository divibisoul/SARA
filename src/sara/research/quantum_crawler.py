"""SARA — Pesquisa: QuantumCrawler.
Status: PENDING_INFRASTRUCTURE
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
import copy
import json
import threading
import time
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
                 source: str = "HTTP",
                 cache_ttl_s: float = 30.0,
                 max_retries: int = 2,
                 backoff_s: float = 0.5) -> None:
        if "{query}" not in endpoint_template:
            raise ValueError("endpoint_template deve conter {query}")
        if timeout_s <= 0:
            raise ValueError("timeout_s deve ser positivo")
        if cache_ttl_s < 0:
            raise ValueError("cache_ttl_s não pode ser negativo")
        if max_retries < 0:
            raise ValueError("max_retries não pode ser negativo")
        if backoff_s < 0:
            raise ValueError("backoff_s não pode ser negativo")
        self.endpoint_template = endpoint_template
        self.token_env = token_env
        self.timeout_s = timeout_s
        self.source = source
        self.cache_ttl_s = cache_ttl_s
        self.max_retries = max_retries
        self.backoff_s = backoff_s
        self._cache: dict[str, tuple[float, list[dict]]] = {}
        self._cache_lock = threading.RLock()

    def describe(self) -> dict:
        return {
            "source": self.source,
            "endpoint_configured": bool(self.endpoint_template),
            "token_env": self.token_env,
            "timeout_s": self.timeout_s,
            "cache_ttl_s": self.cache_ttl_s,
            "max_retries": self.max_retries,
            "backoff_s": self.backoff_s,
            "retry_statuses": [429, 502, 503, 504],
        }

    def fetch(self, query: str) -> list[dict]:
        encoded_query = urllib.parse.quote(str(query), safe="")
        url = self.endpoint_template.format(query=encoded_query)
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
        now = time.monotonic()
        if self.cache_ttl_s > 0:
            with self._cache_lock:
                cached = self._cache.get(url)
                if cached and now - cached[0] < self.cache_ttl_s:
                    return copy.deepcopy(cached[1])

        last_error = None
        payload = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in {429, 502, 503, 504} or attempt >= self.max_retries:
                    detail = exc.read().decode("utf-8", "replace")[:500]
                    raise RuntimeError(f"{self.source} HTTP {exc.code}: {detail}") from exc
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                try:
                    delay = max(0.0, float(retry_after)) if retry_after else self.backoff_s * (2 ** attempt)
                except ValueError:
                    delay = self.backoff_s * (2 ** attempt)
                time.sleep(delay)
            except (urllib.error.URLError, json.JSONDecodeError) as exc:
                last_error = exc
                if isinstance(exc, json.JSONDecodeError) or attempt >= self.max_retries:
                    raise RuntimeError(f"{self.source} backend failure: {exc}") from exc
                time.sleep(self.backoff_s * (2 ** attempt))
        if payload is None:
            raise RuntimeError(f"{self.source} backend failure: {last_error}")

        if isinstance(payload, list):
            items = [item for item in payload if isinstance(item, dict)]
        elif isinstance(payload, dict):
            if isinstance(payload.get("items"), list):
                items = [item for item in payload["items"] if isinstance(item, dict)]
            elif isinstance(payload.get("models"), list):
                items = [item for item in payload["models"] if isinstance(item, dict)]
            else:
                items = [payload]
        else:
            raise RuntimeError(f"{self.source} returned unsupported JSON shape")

        if self.cache_ttl_s > 0:
            with self._cache_lock:
                self._cache[url] = (time.monotonic(), copy.deepcopy(items))
        return items

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
            "backends": [backend.describe() for backend in self._backends if hasattr(backend, "describe")],
        }

    def is_backends_ready(self) -> bool:
        return len(self._backends) > 0

    def scan_configured(self, query: str) -> list[TechCandidate]:
        if not self._backends:
            raise RuntimeError("QUANTUM_CRAWLER_NO_BACKENDS")
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
        if not str(query).strip():
            raise ValueError("query não pode ser vazia")
        if self._backends:
            return self.scan_configured(query)
        raise RuntimeError("QUANTUM_CRAWLER_NO_BACKENDS")

    def verify_source(self, candidate: TechCandidate) -> dict:
        """Validação de origem baseada no backend que produziu o candidato."""
        source = str(candidate.source).strip()
        name = str(candidate.name).strip()
        if not source or not name:
            return {"verified": False, "reason": "candidate_source_or_name_missing"}
        return {
            "verified": False,
            "source_identified": True,
            "source": source,
            "name": name,
            "license_present": bool(str(candidate.license).strip()),
            "verification_mode": "backend_identity_only",
            "reason": "origem identificada pelo backend; autenticidade/licença jurídica exigem consulta verificável",
        }

    def list_sources(self) -> list[str]:
        return ["NVIDIA", "Tesla", "Google", "OpenAI", "HuggingFace"]

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            active = self.is_backends_ready()
            ctx.record(
                "governance",
                self.NAME,
                active,
                reason=(
                    "active_real_http_backends"
                    if active else "PENDING_INFRASTRUCTURE"
                ),
                backends_configured=len(self._backends),
            )