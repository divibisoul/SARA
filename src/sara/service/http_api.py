"""SARA HTTP service v1 — boundary real sobre o runtime modular.

Sem mock/stub: todos os endpoints chamam o runtime real ou retornam erro explícito
quando a capacidade requerida está bloqueada por infraestrutura externa.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from sara.bootstrap import SaraSystem, build_default_system


class SaraAPIError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details or {}


class SaraHTTPHandler(BaseHTTPRequestHandler):
    server_version = "SARA/1.0"

    def _runtime(self) -> SaraSystem:
        return self.server.sara_system  # type: ignore[attr-defined]

    def _json(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _error(self, exc: SaraAPIError) -> None:
        self._json(exc.status, {"error": {"code": exc.code, "message": exc.message, "details": exc.details}})

    def _authorized(self, path: str) -> None:
        if path == "/health":
            return
        expected = os.getenv("SARA_API_TOKEN")
        if not expected:
            raise SaraAPIError(503, "AUTH_NOT_CONFIGURED", "SARA_API_TOKEN não configurado; API protegida por fail-closed.")
        supplied = self.headers.get("Authorization", "")
        if supplied != f"Bearer {expected}":
            raise SaraAPIError(401, "UNAUTHORIZED", "Bearer token inválido ou ausente.")

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
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
            system = self._runtime()
            if path == "/health":
                self._json(200, {
                    "status": "ok" if system.ready else "not_ready",
                    "ready": system.ready,
                    "version": "1.0",
                    "invariants_ok": bool(system.invariant_report.get("ok")),
                })
                return
            if path == "/v1/capabilities":
                modules = system.registry.snapshot()["modules"]
                self._json(200, {
                    "service": "SARA",
                    "contract_version": "1.0",
                    "ready": system.ready,
                    "modules": modules,
                    "activation": system.registration_report.get("pending", []),
                    "invariants": system.invariant_report,
                })
                return
            if path == "/v1/state":
                self._json(200, system.sistema_vivo.state())
                return
            if path.startswith("/v1/trace/"):
                cycle_id = path.rsplit("/", 1)[-1]
                entries = system.components["trace"].query({"cycle_id": cycle_id})
                self._json(200, {
                    "cycle_id": cycle_id,
                    "integrity": system.components["trace"].verify(),
                    "entries": [e.__dict__ for e in entries],
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
                flaws = ara.detect(text)
                structural = ara.detect_structural(text)
                relational = ara.detect_relational(text)
                if path == "/v1/audit":
                    self._json(200, {
                        "operation": "audit",
                        "flaws": [getattr(f, "__dict__", str(f)) for f in [*flaws, *structural, *relational]],
                        "count": len(flaws) + len(structural) + len(relational),
                    })
                    return
                regenerated = ara.regenerate_semantic(text, [*flaws, *structural, *relational])
                self._json(200, {
                    "operation": "regenerate",
                    "original": regenerated.original,
                    "transformed": regenerated.transformed,
                    "applied_rules": list(regenerated.applied_rules),
                    "integrity_hash": regenerated.integrity_hash,
                    "preserved_length": regenerated.preserved_length,
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
    port = int(port or os.getenv("SARA_PORT", "8080"))
    system = build_default_system(fail_closed=fail_closed)
    return SaraHTTPServer((host, port), system)
