"""SARA consumer for N02-owned external capabilities through N07 cooperation.

SARA remains a transversal service, not a Mesh nucleus. It never impersonates an
N0 peer: requests travel SARA -> N07 cooperation.exchange -> N02 owner, and
the N02 runtime may perform the real N07 orbital/Prefrontal preflight.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import urllib.error
import urllib.request
from typing import Any


@dataclass(frozen=True)
class ExternalCapabilityResponse:
    status: int
    correlation_id: str
    payload: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "correlation_id": self.correlation_id, "payload": self.payload}


class N02ExternalCapabilityAdapter:
    OPERATION = "cooperation.exchange@1.0.0"

    def __init__(self, n07_endpoint: str, token: str = "", timeout_s: float = 30.0) -> None:
        endpoint = n07_endpoint.strip().rstrip("/")
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError("n07_endpoint deve ser http/https")
        self.endpoint = endpoint
        self.token = token
        self.timeout_s = timeout_s

    def execute(
        self,
        *,
        capability: str,
        payload: Any,
        correlation_id: str,
        workloads: list[dict[str, Any]] | None = None,
        candidate: dict[str, Any] | None = None,
        strategy: str = "sara-external-capability",
    ) -> ExternalCapabilityResponse:
        capability = capability.strip()
        correlation_id = correlation_id.strip()
        if not capability:
            raise ValueError("capability_required")
        if not correlation_id:
            raise ValueError("correlation_id_required")

        request_payload = {
            "operation": self.OPERATION,
            "payload": [],
            "metadata": {
                "target": "N02",
                "capability": capability,
                "correlation_id": correlation_id,
                "trace_id": correlation_id,
                "payload": json.dumps({
                    "payload": payload,
                    "metadata": {
                        "prefrontal_orbital": "true",
                        "workloads_json": json.dumps(workloads or [], separators=(",", ":")),
                        "candidate_json": json.dumps(candidate or {"capability": capability}, separators=(",", ":")),
                        "strategy": strategy,
                    },
                }, separators=(",", ":")),
            },
        }
        body = json.dumps(request_payload, separators=(",", ":")).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Correlation-ID": correlation_id,
            "User-Agent": "SARA-N02External/1.0",
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
            raise RuntimeError(f"N07_COOPERATION_HTTP_{exc.code}:{detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"N07_COOPERATION_TRANSPORT_ERROR:{exc}") from exc
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("N07_COOPERATION_INVALID_JSON") from exc
        if not isinstance(result, dict):
            raise RuntimeError("N07_COOPERATION_INVALID_RESPONSE")
        return ExternalCapabilityResponse(status=status, correlation_id=correlation_id, payload=result)
