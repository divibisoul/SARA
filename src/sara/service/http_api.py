"""SARA HTTP service v1 — boundary real sobre o runtime modular.

Sem mock/stub: todos os endpoints chamam o runtime real ou retornam erro explícito
quando a capacidade requerida está bloqueada por infraestrutura externa.
"""
from __future__ import annotations

import json
import os
import hmac
import uuid
import time
import threading

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast
from urllib.parse import urlparse

from sara.bootstrap import SaraSystem, build_default_system
from sara.contracts.federation import FederationIdentity, CapabilityDescriptor
from sara.meta.soul_federation import federation_manifest, SARA_OPERATIONS

_RATE_WINDOW_S = 60
_RATE_MAX = 60
_rate_state: dict[str, tuple[int, float]] = {}
_rate_lock = threading.Lock()


class SaraAPIError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details or {}


class SaraHTTPHandler(BaseHTTPRequestHandler):
    server_version = "SARA/3.1.0"

    def _runtime(self) -> SaraSystem:
        return cast(SaraHTTPServer, self.server).sara_system

    def _html(self, status: int, payload: str) -> None:
        raw = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _json(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        correlation = self.headers.get("X-Correlation-ID", "").strip()
        if correlation:
            self.send_header("X-Correlation-ID", correlation)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _error(self, exc: SaraAPIError) -> None:
        self._json(exc.status, {"error": {"code": exc.code, "message": exc.message, "details": exc.details}})

    def _rate_limit(self) -> None:
        now = time.monotonic()
        key = self.client_address[0] if self.client_address else 'unknown'
        with _rate_lock:
            count, started = _rate_state.get(key, (0, now))
            if now - started >= _RATE_WINDOW_S:
                count, started = 0, now
            count += 1
            _rate_state[key] = (count, started)
        if count > _RATE_MAX:
            raise SaraAPIError(429, 'RATE_LIMITED', 'Limite temporário de requisições excedido.', {'window_seconds': _RATE_WINDOW_S, 'max_requests': _RATE_MAX})

    def _authorized(self, path: str) -> None:
        if path == "/health":
            return
        expected = os.getenv("SARA_API_TOKEN")
        if not expected:
            raise SaraAPIError(503, "AUTH_NOT_CONFIGURED", "SARA_API_TOKEN não configurado; API protegida por fail-closed.")
        supplied = self.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied, f"Bearer {expected}"):
            raise SaraAPIError(401, "UNAUTHORIZED", "Bearer token inválido ou ausente.")

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > (1 << 20):
                raise ValueError("request body exceeds 1 MiB")
            data = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(data, dict):
                raise ValueError("JSON deve ser objeto")
            return data
        except Exception as exc:
            raise SaraAPIError(400, "INVALID_JSON", str(exc)) from exc

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            self._authorized(path)
            self._rate_limit()
            system = self._runtime()
            if path == "/health":
                self._json(200, {
                    "service": "SARA",
                    "status": "ok" if system.ready else "not_ready",
                    "ready": system.ready,
                    "version": "3.1.0",
                    "protocol": "sara-http/1",
                    "invariants_ok": bool(system.invariant_report.get("ok")),
                    "trace_integrity": system.components["trace"].verify(),
                    "provenance_integrity": system.components["provenance"].verify_integrity(),
                    "rollback_chain_integrity": system.components["rollback"].verify_chain(),
                    "module_count": system.registry.snapshot()["count"],
                    "pending_infrastructure": system.registry.by_status().get("PENDING_INFRASTRUCTURE", []),
                })
                return
            if path == "/v1/capabilities":
                modules = system.registry.snapshot()["modules"]
                operation_specs = {
                    "sara.health@1.0.0": ("/health", ("monitoring",)),
                    "sara.cycle@1.0.0": (
                        "/v1/cycle",
                        tuple(p.value for p in system.components["loop"].CYCLE_PHASES),
                    ),
                    "sara.audit@1.0.0": (
                        "/v1/audit",
                        ("audit", "ethics", "validation"),
                    ),
                    "sara.regenerate@1.0.0": (
                        "/v1/regenerate",
                        ("audit", "regeneration", "ethics", "validation"),
                    ),
                    "sara.state@1.0.0": (
                        "/v1/state",
                        (),
                    ),
                    "sara.trace@1.0.0": (
                        "/v1/trace/{cycle_id}",
                        ("persistence", "monitoring"),
                    ),
                }
                descriptors = [
                    CapabilityDescriptor(
                        name=op.split("@", 1)[0],
                        version=op.split("@", 1)[1],
                        operation=op,
                        endpoint=spec[0],
                        phases=spec[1],
                        status="IMPLEMENTED",
                        requires_auth=bool(SARA_OPERATIONS.get(op.split("@", 1)[0], {}).get("requires_auth", True)),
                    ).as_dict()
                    for op, spec in operation_specs.items()
                ]
                identity = FederationIdentity(node_id="SARA", node_name="SARA")
                self._json(200, {
                    "service": "SARA",
                    "protocol": "sara-http/1",
                    "contract_version": identity.protocol_version,
                    "identity": identity.as_dict(),
                    "ready": system.ready,
                    "operations": [
                        "sara.health@1.0.0",
                        "sara.cycle@1.0.0",
                        "sara.audit@1.0.0",
                        "sara.regenerate@1.0.0",
                        "sara.state@1.0.0",
                        "sara.trace@1.0.0",
                    ],
                    "phases": [p.value for p in system.components["loop"].CYCLE_PHASES],
                    "modules": modules,
                    "capability_descriptors": descriptors,
                    "activation": system.registration_report.get("pending", []),
                    "memory_layers": {
                        "working": system.components["working_memory"].describe(),
                        "episodic": system.components["memory"].describe(),
                        "semantic_vector": system.components["temporal"].describe(),
                    },
                    "provenance_integrity": system.components["provenance"].verify_integrity() if "provenance" in system.components else None,
                    "rollback_chain_integrity": system.components["rollback"].verify_chain(),
                    "invariants": system.invariant_report,
                    "soul_federation": federation_manifest(),
                })
                return
            if path == "/v1/state":
                self._json(200, system.sistema_vivo.state())
                return
            if path == "/v1/governance/ui":
                governance = system.components["governance"]
                self._html(200, governance.render_html())
                return
            if path.startswith("/v1/trace/"):
                cycle_id = path.rsplit("/", 1)[-1]
                entries = system.components["trace"].query({"cycle_id": cycle_id})
                temporal = system.components["temporal"].by_data({"cycle_id": cycle_id})
                self._json(200, {
                    "cycle_id": cycle_id,
                    "integrity": system.components["trace"].verify(),
                    "provenance_integrity": system.components["provenance"].verify_integrity() if "provenance" in system.components else None,
                    "entries": [e.__dict__ for e in entries],
                    "temporal_records": [r.__dict__ for r in temporal],
                })
                return
            raise SaraAPIError(404, "NOT_FOUND", f"Endpointo não existe: {path}")
        except SaraAPIError as exc:
            self._error(exc)
        except Exception as exc:
            self._error(SaraAPIError(500, "INTERNAL_ERROR", str(exc)))

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            self._authorized(path)
            system = self._runtime()
            body = self._body()
            if not system.ready:
                raise SaraAPIError(503, "NOT_READY", "SARA não passou pelas invariantes de bootstrap.", system.invariant_report)

            if path == "/v1/cycle":
                text = body.get("input")
                if not isinstance(text, str) or not text.strip():
                    raise SaraAPIError(422, "INVALID_INPUT", "'input' deve ser string não vazia.")
                cycle_id = body.get("cycle_id")
                correlation = self.headers.get("X-Correlation-ID", "").strip()
                if cycle_id is None and correlation:
                    cycle_id = correlation
                if cycle_id is not None and (
                    not isinstance(cycle_id, str) or not cycle_id.strip()
                ):
                    raise SaraAPIError(422, "INVALID_CYCLE_ID", "'cycle_id' deve ser string não vazia.")
                result = system.sistema_vivo.process(text, cycle_id=cycle_id)
                self._json(200, {
                    "cycle_id": result.cycle_id,
                    "input": result.input,
                    "final_state": result.loop_report.final_state,
                    "converged": result.loop_report.converged,
                    "rollback_performed": result.loop_report.rollback_performed,
                    "execution_report": result.loop_report.execution_report,
                    "trace_hash": result.trace_hash,
                })
                return

            if path in ("/v1/audit", "/v1/regenerate"):
                text = body.get("input")
                if not isinstance(text, str) or not text.strip():
                    raise SaraAPIError(422, "INVALID_INPUT", "'input' deve ser string não vazia.")
                ara = system.components["ara_extended"]
                etr = system.components["etr_extended"]
                flaws = ara.detect(text)
                semantic = ara.detect_semantic(text)
                structural = ara.detect_structural(text)
                relational = ara.detect_relational(text)
                all_flaws = [*flaws, *semantic, *structural, *relational]
                if path == "/v1/audit":
                    ethical = etr.validate_multi_framework(text)
                    request_id = self.headers.get("X-Correlation-ID", "").strip() or str(uuid.uuid4())
                    self._json(200, {
                        "request_id": request_id,
                        "correlation_id": request_id,
                        "operation": "audit",
                        "flaws": [getattr(f, "__dict__", str(f)) for f in all_flaws],
                        "count": len(all_flaws),
                        "semantic": [getattr(f, "__dict__", str(f)) for f in semantic],
                        "ethical": getattr(ethical, "__dict__", str(ethical)),
                        "provenance": ara.meta_audit_complete(),
                    })
                    return
                regenerated = ara.regenerate_semantic(text, all_flaws)
                ethical = etr.validate_multi_framework(regenerated.transformed)
                request_id = self.headers.get("X-Correlation-ID", "").strip() or str(uuid.uuid4())
                self._json(200, {
                    "request_id": request_id,
                    "correlation_id": request_id,
                    "operation": "regenerate",
                    "original": regenerated.original,
                    "transformed": regenerated.transformed,
                    "applied_rules": list(regenerated.applied_rules),
                    "plan_steps": list(regenerated.plan_steps),
                    "integrity_hash": regenerated.integrity_hash,
                    "preserved_length": regenerated.preserved_length,
                    "ethical": getattr(ethical, "__dict__", str(ethical)),
                })
                return

            raise SaraAPIError(404, "NOT_FOUND", f"Endpointo não existe: {path}")
        except SaraAPIError as exc:
            self._error(exc)
        except Exception as exc:
            self._error(SaraAPIError(500, "INTERNAL_ERROR", str(exc)))

    def log_message(self, fmt: str, *args: Any) -> None:
        # Mantém o logging do servidor sem poluir stdout com dados de entrada.
        return


class SaraHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], sara_system: SaraSystem):
        self.sara_system = sara_system
        super().__init__(address, SaraHTTPHandler)


def create_server(host: str | None = None, port: int | None = None, *, fail_closed: bool = True) -> SaraHTTPServer:
    host = host or os.getenv("SARA_HOST", "127.0.0.1")
    port = int(os.getenv("SARA_PORT", "8080")) if port is None else int(port)
    system = build_default_system(fail_closed=fail_closed)
    return SaraHTTPServer((host, port), system)
