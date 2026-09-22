"""Contratos externos de federação do SARA.

Este arquivo define envelopes de protocolo, não implementa rede nem finge integração
com N07. A camada HTTP implementa o transporte; N07 pode mapear seus envelopes
execute/intent para estas estruturas sem acoplamento ao núcleo interno.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Literal
from uuid import uuid4


IntentKind = Literal["cycle", "audit", "regenerate", "state", "trace"]


@dataclass(frozen=True)
class FederationIdentity:
    node_id: str
    node_name: str = "SARA"
    protocol_version: str = "1.0"


@dataclass(frozen=True)
class IntentEnvelope:
    intent_id: str
    source_node: str
    target_node: str
    kind: IntentKind
    payload: dict[str, Any]
    trace_id: str | None = None
    deadline_ms: int | None = None
    idempotency_key: str | None = None

    @classmethod
    def create(cls, source_node: str, target_node: str, kind: IntentKind,
               payload: dict[str, Any], *, trace_id: str | None = None,
               deadline_ms: int | None = None, idempotency_key: str | None = None) -> "IntentEnvelope":
        return cls(str(uuid4()), source_node, target_node, kind, dict(payload),
                   trace_id, deadline_ms, idempotency_key)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExecuteEnvelope:
    intent_id: str
    operation: str
    payload: dict[str, Any]
    authorization: str
    trace_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityDescriptor:
    name: str
    version: str
    operation: str
    endpoint: str
    phases: tuple[str, ...]
    status: str
    requires_auth: bool = True
    requires_external_infrastructure: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecuteResult:
    intent_id: str
    status: Literal["accepted", "completed", "rejected", "failed"]
    cycle_id: str | None
    trace_id: str | None
    result: dict[str, Any]
    error_code: str | None = None
    error_message: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HealthReport:
    node: FederationIdentity
    ready: bool
    invariants_ok: bool
    active_capabilities: int
    pending_capabilities: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
