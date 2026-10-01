"""SARA consumer adapter for the canonical N07 orbital/Prefrontal boundary.

SARA does not own TCE or Prefrontal. It consumes the N07 capability through an
explicitly configured HTTP endpoint and preserves correlation/provenance.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import urllib.error
import urllib.request
from typing import Any


@dataclass(frozen=True)
class OrbitalPrefrontalResponse:
    status: str
    correlation_id: str
    payload: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
        }


class N07OrbitalPrefrontalAdapter:
    """Real HTTP consumer of N07 prefrontal.orbital.evaluate."""

    OPERATION = "prefrontal.orbital.evaluate@1.0.0"

    def __init__(self, endpoint: str, token: str = "", timeout_s: float = 30.0) -> None:
        endpoint = endpoint.strip().rstrip("/")
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError("endpoint deve ser http/https")
        self.endpoint = endpoint
        self.token = token
        self.timeout_s = timeout_s

    def evaluate(
        self,
        *,
        correlation_id: str,
        payload: list[float],
        workloads: list[dict[str, Any]],
        candidate: dict[str, Any],
        strategy: str = "auto",
    ) -> OrbitalPrefrontalResponse:
        if not correlation_id.strip():
            raise ValueError("correlation_id_required")
        body = json.dumps({
            "operation": self.OPERATION,
            "payload": payload,
            "metadata": {
                "workloads_json": json.dumps(workloads, separators=(",", ":")),
                "candidate_json": json.dumps(candidate, separators=(",", ":")),
                "strategy": strategy,
            },
        }).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Correlation-ID": correlation_id,
            "User-Agent": "SARA-OrbitalPrefrontal/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            f"{self.endpoint}/execute",
            data=body,
            method="POST",
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                raw = response.read().decode("utf-8")
                status = int(response.status)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:1000]
            raise RuntimeError(f"N07_ORBITAL_HTTP_{exc.code}:{detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"N07_ORBITAL_TRANSPORT_ERROR:{exc}") from exc
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("N07_ORBITAL_INVALID_JSON") from exc
        if not isinstance(result, dict):
            raise RuntimeError("N07_ORBITAL_INVALID_RESPONSE")
        return OrbitalPrefrontalResponse(status=str(status), correlation_id=correlation_id, payload=result)
