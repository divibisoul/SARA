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
from sara.meta.soul_external_fabric import fabric_manifest, resolve_external_provider, providers_for_function
from sara.meta.resident_agent import SARA_RESIDENT_AGENT
from sara.meta.n02_external_capability import N02ExternalCapabilityAdapter
from sara.rgo.contracts import RGOValidationError
from sara.integrations import mem0

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
                    "rgo.ingest@1.0.0": ("/v1/rgo/ingest", ("governance", "persistence", "monitoring")),
                    "rgo.state@1.0.0": ("/v1/rgo/state", ("monitoring", "persistence")),
                    "rgo.trinity.process@1.0.0": ("/v1/rgo/trinity", ("ingestion", "audit", "strategy", "ethics", "regeneration", "execution", "persistence", "monitoring")),
                    "sara.external.capability@1.0.0": ("/v1/external/capability", ("audit", "strategy", "execution", "validation", "monitoring")),
                    "mem0.status@1.0.0": ("/v1/mem0/status", ("monitoring",)),
                    "mem0.add@1.0.0": ("/v1/mem0/add", ("persistence",)),
                    "mem0.search@1.0.0": ("/v1/mem0/search", ("persistence", "monitoring")),
                    "mem0.list@1.0.0": ("/v1/mem0/list", ("persistence", "monitoring")),
                    "external.capability.resolve@1.0.0": ("/v1/external/resolve", ("monitoring", "governance")),
                    "external.capability.fabric.describe@1.0.0": ("/v1/external/fabric", ("monitoring", "governance")),
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
                        "sara.hortacore.assess@1.0.0",
                        "sara.audit@1.0.0",
                        "sara.regenerate@1.0.0",
                        "sara.state@1.0.0",
                        "sara.trace@1.0.0",
                        "rgo.ingest@1.0.0",
                        "rgo.state@1.0.0",
                        "rgo.trinity.process@1.0.0",
                        "sara.external.capability@1.0.0",
                        "mem0.status@1.0.0",
                        "mem0.add@1.0.0",
                        "mem0.search@1.0.0",
                        "mem0.list@1.0.0",
                        "external.capability.resolve@1.0.0",
                        "external.capability.fabric.describe@1.0.0",
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
            if path == "/v1/octacore":
                fusion = system.components.get("octacore_fusion")
                if fusion is None:
                    raise SaraAPIError(503, "OCTACORE_FUSION_UNAVAILABLE", "OctaCore fusion fabric indisponível.")
                self._json(200, {
                    "service": "SARA",
                    "operation": "octacore",
                    "identity": "G0",
                    "manifest": fusion.describe(),
                    "health": fusion.health(),
                    "audit": fusion.audit(),
                })
                return
            if path == "/v1/mesh/status":
                fusion = system.components.get("octacore_fusion")
                if fusion is None:
                    raise SaraAPIError(503, "MESH_FUSION_UNAVAILABLE", "Mesh fusion fabric indisponível.")
                health = fusion.health()
                self._json(200, {
                    "service": "SARA",
                    "operation": "mesh.status",
                    "mesh": fusion.describe().get("mesh", {}),
                    "health": health,
                    "last_probe": health.get("mesh_last_probe"),
                    "proof": {
                        "configured": bool(os.getenv("SOUL_MESH_N01_URL", "").strip()),
                        "connected": bool(health.get("mesh_last_probe") and health["mesh_last_probe"].get("status") in {"CONNECTED", "VERIFIED"}),
                        "verified": bool(health.get("mesh_last_probe") and health["mesh_last_probe"].get("status") == "VERIFIED"),
                        "unmeasurable_without_probe": health.get("mesh_last_probe") is None,
                    },
                })
                return
            if path == "/v1/state":
                self._json(200, system.sistema_vivo.state())
                return
            if path == "/v1/rgo/state":
                state = system.components["rgo"].state()
                self._json(200, state.__dict__)
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

            if path == "/v1/external/fabric":
                self._json(200, {
                    "operation": "external.capability.fabric.describe",
                    "fabric": fabric_manifest(),
                    "resident_agent": SARA_RESIDENT_AGENT,
                })
                return

            if path == "/v1/resident":
                self._json(200, SARA_RESIDENT_AGENT)
                return

            if path == "/v1/mem0/status":
                self._json(200, mem0.status())
                return

            if path == "/v1/mem0/add":
                messages = body.get("messages", body.get("message", ""))
                try:
                    result = mem0.add(messages, user_id=body.get("user_id"), metadata=body.get("metadata"))
                except (RuntimeError, ValueError) as exc:
                    raise SaraAPIError(502, "MEM0_ADD_FAILED", str(exc)) from exc
                self._json(200, {"operation": "mem0.add", "provider": "mem0ai/mem0", "upstream_commit": mem0.UPSTREAM_COMMIT, "result": result})
                return

            if path == "/v1/mem0/search":
                query = body.get("query", "")
                try:
                    result = mem0.search(query, user_id=body.get("user_id"), top_k=body.get("top_k"), filters=body.get("filters"))
                except (RuntimeError, ValueError) as exc:
                    raise SaraAPIError(502, "MEM0_SEARCH_FAILED", str(exc)) from exc
                self._json(200, {"operation": "mem0.search", "provider": "mem0ai/mem0", "upstream_commit": mem0.UPSTREAM_COMMIT, "result": result})
                return

            if path == "/v1/mem0/list":
                try:
                    result = mem0.get_all(user_id=body.get("user_id"), page=body.get("page"), page_size=body.get("page_size"), filters=body.get("filters"))
                except (RuntimeError, ValueError) as exc:
                    raise SaraAPIError(502, "MEM0_LIST_FAILED", str(exc)) from exc
                self._json(200, {"operation": "mem0.list", "provider": "mem0ai/mem0", "upstream_commit": mem0.UPSTREAM_COMMIT, "result": result})
                return

            if path == "/v1/external/resolve":
                provider = str(body.get("provider", "")).strip()
                function_id = str(body.get("function", "")).strip()
                if provider:
                    try:
                        item = resolve_external_provider(provider)
                    except ValueError as exc:
                        raise SaraAPIError(404, "EXTERNAL_PROVIDER_UNKNOWN", str(exc)) from exc
                    self._json(200, {"operation": "external.capability.resolve", "provider": item.__dict__})
                    return
                if function_id:
                    self._json(200, {"operation": "external.capability.resolve", "function": function_id, "providers": [item.__dict__ for item in providers_for_function(function_id)]})
                    return
                raise SaraAPIError(422, "EXTERNAL_PROVIDER_OR_FUNCTION_REQUIRED", "provider ou function é obrigatório.")

            if path == "/v1/external/capability":
                endpoint = os.getenv("SOUL_MESH_N07_URL", "").strip()
                if not endpoint:
                    raise SaraAPIError(503, "N07_ENDPOINT_NOT_CONFIGURED", "SOUL_MESH_N07_URL não configurado; delegação externa permanece fechada.")
                capability = body.get("capability")
                correlation = self.headers.get("X-Correlation-ID", "").strip() or str(uuid.uuid4())
                if not isinstance(capability, str) or not capability.strip():
                    raise SaraAPIError(422, "CAPABILITY_REQUIRED", "'capability' deve ser string não vazia.")
                payload = body.get("payload", {})
                workloads = body.get("workloads", [])
                candidate = body.get("candidate", {})
                strategy = body.get("strategy", "sara-external-capability")
                if not isinstance(workloads, list):
                    raise SaraAPIError(422, "WORKLOADS_MUST_BE_ARRAY", "'workloads' deve ser array.")
                if not isinstance(candidate, dict):
                    raise SaraAPIError(422, "CANDIDATE_MUST_BE_OBJECT", "'candidate' deve ser objeto.")
                adapter = N02ExternalCapabilityAdapter(
                    endpoint,
                    token=os.getenv("N07_APP_TOKEN", "").strip(),
                )
                result = adapter.execute(
                    capability=capability,
                    payload=payload,
                    correlation_id=correlation,
                    workloads=workloads,
                    candidate=candidate,
                    strategy=strategy if isinstance(strategy, str) else "sara-external-capability",
                )
                self._json(200 if result.status < 400 else result.status, {
                    "operation": "sara.external.capability",
                    "correlation_id": result.correlation_id,
                    "status": result.status,
                    "result": result.payload,
                })
                return

            if path == "/v1/hortacore/assess":
                proposal = body.get("proposal")
                if not isinstance(proposal, dict):
                    raise SaraAPIError(422, "INVALID_PROPOSAL", "'proposal' deve ser objeto.")
                bridge = system.components.get("aeternum_chimera")
                if bridge is None:
                    raise SaraAPIError(503, "AETERNUM_CHIMERA_UNAVAILABLE", "AeternumChimeraBridge indisponível.")
                result = bridge.fuse_assessment(proposal)
                correlation = self.headers.get("X-Correlation-ID", "").strip() or str(uuid.uuid4())
                self._json(200, {
                    "request_id": correlation,
                    "correlation_id": correlation,
                    "operation": "hortacore_assess",
                    "authority": "AeternumChimeraBridge",
                    "assessment": result,
                })
                return

            if path == "/v1/mesh/probe":
                fusion = system.components.get("octacore_fusion")
                if fusion is None:
                    raise SaraAPIError(503, "MESH_FUSION_UNAVAILABLE", "Mesh fusion fabric indisponível.")
                target = str(body.get("mediator", "N01")).strip().upper()
                try:
                    probe = fusion.probe_mesh(mediator=target)
                except ValueError as exc:
                    raise SaraAPIError(422, "INVALID_MESH_MEDIATOR", str(exc)) from exc
                status_code = 200 if probe.status in {"CONNECTED", "VERIFIED", "UNMEASURABLE"} else 502
                self._json(status_code, {"operation": "mesh.probe", "probe": probe.as_dict()})
                return

            if path == "/v1/vagus":
                bus = system.components.get("vagus_bus")
                if bus is None:
                    raise SaraAPIError(503, "VAGUS_BUS_UNAVAILABLE", "Vagus control plane indisponível.")
                required = ("vagus_version", "message_id", "correlation_id", "source", "target", "priority", "ttl", "type", "payload")
                missing = [key for key in required if key not in body]
                if missing:
                    raise SaraAPIError(422, "INVALID_VAGUS_ENVELOPE", "Campos obrigatórios ausentes.", {"missing": missing})
                try:
                    vagus_version = str(body["vagus_version"]).strip()
                    message_id = str(body["message_id"]).strip()
                    correlation_id = str(body["correlation_id"]).strip()
                    source = str(body["source"]).strip()
                    target = str(body["target"]).strip()
                    event_type = str(body["type"]).strip()
                    priority = int(body["priority"])
                    ttl = int(body["ttl"])
                except (TypeError, ValueError) as exc:
                    raise SaraAPIError(422, "INVALID_VAGUS_ENVELOPE", "Envelope Vagus inválido.") from exc
                payload = body["payload"]
                if not isinstance(payload, dict):
                    raise SaraAPIError(422, "INVALID_VAGUS_ENVELOPE", "'payload' deve ser objeto JSON.")
                if vagus_version != "1.0":
                    raise SaraAPIError(422, "INVALID_VAGUS_VERSION", "Vagus version não suportada.")
                if not message_id or not correlation_id or not source or not target or not event_type or not 0 <= priority <= 100 or ttl <= 0:
                    raise SaraAPIError(422, "INVALID_VAGUS_ENVELOPE", "Envelope Vagus incompleto.")
                event = bus.publish_sync(
                    source,
                    target,
                    event_type,
                    payload,
                    status=str(body.get("status", "EXECUTE")).strip() or "EXECUTE",
                    correlation_id=correlation_id,
                    message_id=message_id,
                    priority=priority,
                    ttl=ttl,
                )
                self._json(200, {"operation": "vagus", "event": event})
                return

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
                federated_context = body.get("context", {})
                if federated_context is None:
                    federated_context = {}
                if not isinstance(federated_context, dict):
                    raise SaraAPIError(422, "INVALID_CONTEXT", "'context' deve ser objeto JSON.")
                result = system.sistema_vivo.process(text, cycle_id=cycle_id, federated_context=federated_context)
                correlation_id = correlation or result.cycle_id
                self._json(200, {
                    "request_id": correlation_id,
                    "correlation_id": correlation_id,
                    "cycle_id": result.cycle_id,
                    "input": result.input,
                    "final_state": result.loop_report.final_state,
                    "converged": result.loop_report.converged,
                    "rollback_performed": result.loop_report.rollback_performed,
                    "execution_report": result.loop_report.execution_report,
                    "trace_hash": result.trace_hash,
                    "federated_context_hash": result.federated_context_hash,
                })
                return

            if path == "/v1/rgo/ingest":
                try:
                    finding = body.get("finding", body)
                    result = system.components["rgo"].ingest(finding)
                except RGOValidationError as exc:
                    raise SaraAPIError(422, "RGO_INVALID", str(exc)) from exc
                self._json(200, result)
                return

            if path == "/v1/rgo/trinity":
                try:
                    result = system.components["trinity_rgo"].process(body.get("finding", body), cycle_id=body.get("cycle_id"))
                except RGOValidationError as exc:
                    raise SaraAPIError(422, "RGO_INVALID", str(exc)) from exc
                self._json(200, result.as_dict())
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
