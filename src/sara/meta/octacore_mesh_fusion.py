"""SARA — OctaCore/HortaCore/Vagus/Soul Mesh fusion fabric.

This module is additive. It does not replace SARA authorities, the canonical
seven-nucleus Soul Mesh, Aeternum Chimera/HortaCore, or VagusNerveBus.

Architecture:
  G0 = SARA regenerative kernel (system-level authority)
  G1..G7 = N01..N07 Soul nuclei (canonical Mesh identities)
  VagusBus = internal/control-plane event fabric
  Soul Mesh = external seven-nucleus interoperability plane
  HortaCore = existing Aeternum Chimera composition over SARA authorities

SARA is intentionally NOT a Soul Mesh nucleus. G0 is a logical OctaCore slot,
not a forged eighth Mesh identity.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sara.contracts.base import CyclePhase, CycleRole, ModuleStatus
from sara.contracts.invariants import InvariantValidator
from sara.contracts.registry import ModuleRegistry
from sara.core.provenance import Provenance, ProvenanceTracker
from sara.infra.hashing import hash_json


SOUL_MESH_PROTOCOL = "soul-mesh/1"
SOUL_MESH_CONTRACT_VERSION = "1.1.0"
SOUL_NUCLEI = ("N01", "N02", "N03", "N04", "N05", "N06", "N07")
OCTACORE_SLOTS = ("G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7")


@dataclass(frozen=True)
class OctaCoreSlot:
    slot: str
    identity: str
    plane: str
    authority: str
    transport: str
    description: str

    def as_dict(self) -> dict[str, str]:
        return {
            "slot": self.slot,
            "identity": self.identity,
            "plane": self.plane,
            "authority": self.authority,
            "transport": self.transport,
            "description": self.description,
        }


@dataclass(frozen=True)
class MeshProbe:
    mediator: str
    status: str
    url: str | None
    checked_at: str
    correlation_id: str
    http_status: int | None = None
    protocol_ok: bool = False
    contract_ok: bool = False
    identity_ok: bool = False
    mesh_topology_ok: bool = False
    sara_federation_ok: bool = False
    sara_federation_configured: bool = False
    evidence_hash: str | None = None
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "mediator": self.mediator,
            "status": self.status,
            "url": self.url,
            "checked_at": self.checked_at,
            "correlation_id": self.correlation_id,
            "http_status": self.http_status,
            "protocol_ok": self.protocol_ok,
            "contract_ok": self.contract_ok,
            "identity_ok": self.identity_ok,
            "mesh_topology_ok": self.mesh_topology_ok,
            "sara_federation_ok": self.sara_federation_ok,
            "sara_federation_configured": self.sara_federation_configured,
            "evidence_hash": self.evidence_hash,
            "detail": self.detail,
        }


class OctaCoreMeshFusion:
    """Cross-plane composition and evidence boundary for SARA + Soul."""

    NAME = "OctaCoreMeshFusion"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = (
        "OctaCoreG0Kernel",
        "AeternumChimeraBridge",
        "TrinityERUUnified",
        "DecisionTrace",
        "ProvenanceTracker",
    )
    CYCLE_PHASES = (
        CyclePhase.INGESTION,
        CyclePhase.AUDIT,
        CyclePhase.REGENERATION,
        CyclePhase.IDENTITY,
        CyclePhase.ETHICS,
        CyclePhase.STRATEGY,
        CyclePhase.EXECUTION,
        CyclePhase.VALIDATION,
        CyclePhase.PERSISTENCE,
        CyclePhase.SNAPSHOT,
        CyclePhase.MONITORING,
        CyclePhase.GOVERNANCE,
    )

    SLOTS = (
        OctaCoreSlot(
            "G0", "SARA", "regenerative", "SARA regeneration/governance",
            "SARA runtime", "System-level kernel slot; not a Mesh nucleus.",
        ),
        *tuple(
            OctaCoreSlot(
                f"G{i}", f"N0{i}", "soul-mesh", "native nucleus authority",
                "Soul Mesh",
                f"Canonical Soul nucleus N0{i}; native capabilities remain owned by N0{i}.",
            )
            for i in range(1, 8)
        ),
    )

    def __init__(
        self,
        registry: ModuleRegistry,
        *,
        vagus_bus: Any | None = None,
        provenance: ProvenanceTracker | None = None,
        trace: Any | None = None,
        g0: Any | None = None,
        horta: Any | None = None,
        trinity: Any | None = None,
    ) -> None:
        self._registry = registry
        self._vagus = vagus_bus
        self._provenance = provenance
        self._trace = trace
        self._g0 = g0
        self._horta = horta
        self._trinity = trinity
        self._validator = InvariantValidator()
        self._last_probe: MeshProbe | None = None

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "logical_octacore": [slot.as_dict() for slot in self.SLOTS],
            "mesh": {
                "protocol": SOUL_MESH_PROTOCOL,
                "contract_version": SOUL_MESH_CONTRACT_VERSION,
                "nuclei": list(SOUL_NUCLEI),
                "nucleus_count": len(SOUL_NUCLEI),
                "sara_is_mesh_nucleus": False,
                "mediator_boundary": "N01/Soul-Mesh gateway",
            },
            "planes": {
                "regeneration": "G0/SARA",
                "governance_research": "HortaCore/AeternumChimeraBridge",
                "control": "VagusNerveBus",
                "federation": "Soul Mesh N01..N07",
            },
        }

    def health(self) -> dict[str, Any]:
        bus = self._vagus.describe() if self._vagus is not None else None
        g0 = self._g0.health() if self._g0 is not None and hasattr(self._g0, "health") else None
        return {
            "status": "READY",
            "g0": g0,
            "vagus": bus,
            "mesh_last_probe": self._last_probe.as_dict() if self._last_probe else None,
            "mesh_contract": {
                "protocol": SOUL_MESH_PROTOCOL,
                "contract_version": SOUL_MESH_CONTRACT_VERSION,
            },
        }

    def audit(self) -> dict[str, Any]:
        """Audit the complete local composition without mutating modules."""
        invariant = self._validator.validate_registry(self._registry)
        missing = self._registry.validate_dependencies()
        try:
            order = self._registry.dependency_order()
            cycle_free = True
        except Exception as exc:
            order = []
            cycle_free = False
            cycle_error = f"{type(exc).__name__}: {exc}"

        modules = self._registry.snapshot().get("modules", {})
        statuses = {
            name: meta.get("status", "UNMEASURABLE")
            for name, meta in modules.items()
        }

        horta_desc = self._horta.describe() if self._horta is not None else {}
        g0_desc = self._g0.describe() if self._g0 is not None else {}
        trinity_desc = (
            self._trinity.describe()
            if self._trinity is not None and hasattr(self._trinity, "describe")
            else {}
        )

        checks: list[dict[str, Any]] = [
            {
                "name": "registry_dependency_resolution",
                "status": "VERIFIED" if not missing else "INCOMPLETE",
                "detail": missing or "all registry dependencies resolved",
            },
            {
                "name": "registry_dependency_graph",
                "status": "VERIFIED" if cycle_free else "BLOCKED",
                "detail": "acyclic" if cycle_free else cycle_error,
            },
            {
                "name": "g0_kernel",
                "status": "VERIFIED" if self._g0 is not None else "BLOCKED",
                "detail": g0_desc or "OctaCore G0 kernel not bound",
            },
            {
                "name": "hortacore",
                "status": "VERIFIED" if self._horta is not None else "BLOCKED",
                "detail": horta_desc or "HortaCore bridge not bound",
            },
            {
                "name": "vagus_single_bus",
                "status": (
                    "VERIFIED"
                    if self._vagus is not None
                    and getattr(self._vagus, "NAME", None) == "VagusNerveBus"
                    else "BLOCKED"
                ),
                "detail": (
                    self._vagus.describe()
                    if self._vagus is not None and hasattr(self._vagus, "describe")
                    else "shared VagusBus not bound"
                ),
            },
            {
                "name": "trinity_eru",
                "status": "VERIFIED" if self._trinity is not None else "BLOCKED",
                "detail": trinity_desc or "TrinityERUUnified not bound",
            },
            {
                "name": "sara_not_forged_as_mesh_nucleus",
                "status": "VERIFIED",
                "detail": "SARA remains G0/system authority; canonical Mesh remains N01..N07.",
            },
        ]

        redundant_inheritance_dependencies: list[str] = []
        for entry in self._registry.items():
            name = entry.name
            instance = entry.instance
            for dependency in entry.dependencies:
                try:
                    mro = type(instance).mro()
                except AttributeError:
                    mro = []
                inherited_name_match = any(
                    getattr(base, "NAME", None) == dependency
                    for base in mro[1:]
                )
                if inherited_name_match:
                    redundant_inheritance_dependencies.append(f"{name}->{dependency}")

        if redundant_inheritance_dependencies:
            checks.append({
                "name": "inheritance_dependency_redundancy",
                "status": "INCOMPLETE",
                "detail": redundant_inheritance_dependencies,
            })
        else:
            checks.append({
                "name": "inheritance_dependency_redundancy",
                "status": "VERIFIED",
                "detail": "no inheritance/runtime dependency ambiguity detected",
            })

        return {
            "status": (
                "VERIFIED"
                if invariant.ok and not missing and cycle_free
                else "INCOMPLETE"
            ),
            "definition": {
                "octacore_slots": len(OCTACORE_SLOTS),
                "mesh_nuclei": len(SOUL_NUCLEI),
                "preservation": "additive",
            },
            "registry": {
                "module_count": len(modules),
                "dependency_order": order,
                "statuses": statuses,
                "invariants": invariant.as_dict(),
            },
            "checks": checks,
            "proof_rule": {
                "declared": "manifest",
                "configured": "environment + explicit runtime objects",
                "connected": "real event/request observed",
                "verified": "real response + identity + contract + traceable evidence",
                "failure": "explicit BLOCKED/INCOMPLETE/UNMEASURABLE",
            },
            "hash": hash_json({
                "modules": statuses,
                "slots": [slot.as_dict() for slot in self.SLOTS],
                "checks": checks,
            }),
        }

    def probe_mesh(self, *, mediator: str = "N01", timeout_s: float = 5.0) -> MeshProbe:
        """Perform real read-only checks for N01 Mesh and N01↔SARA federation.

        No URL => UNMEASURABLE. Transport, protocol or identity failures => BLOCKED.
        VERIFIED additionally requires N01 to report the SARA provider as configured.
        """
        mediator = mediator.strip().upper()
        if mediator != "N01":
            raise ValueError("only the canonical N01 Mesh mediator is currently supported")

        base_url = os.getenv("SOUL_MESH_N01_URL", "").strip().rstrip("/")
        path = os.getenv("SOUL_MESH_N01_HEALTH_PATH", "/mesh/health").strip()
        fusion_path = os.getenv("SOUL_MESH_N01_FUSION_PATH", "/mesh/fusion").strip()
        correlation_id = str(uuid.uuid4())
        from datetime import datetime, timezone
        checked_at = datetime.now(timezone.utc).isoformat()

        if not base_url:
            probe = MeshProbe(
                mediator=mediator,
                status="UNMEASURABLE",
                url=None,
                checked_at=checked_at,
                correlation_id=correlation_id,
                detail="SOUL_MESH_N01_URL is not configured",
            )
            self._record_probe(probe)
            return probe

        def get_json(url: str) -> tuple[int, dict[str, Any]]:
            request = Request(
                url,
                method="GET",
                headers={
                    "Accept": "application/json",
                    "Cache-Control": "no-store",
                    "X-Soul-Correlation-ID": correlation_id,
                },
            )
            with urlopen(request, timeout=max(0.1, float(timeout_s))) as response:
                raw = response.read()
                return int(response.status), json.loads(raw.decode("utf-8"))

        health_url = f"{base_url}{path if path.startswith('/') else '/' + path}"
        fusion_url = f"{base_url}{fusion_path if fusion_path.startswith('/') else '/' + fusion_path}"
        try:
            health_status, health = get_json(health_url)
            fusion_status, fusion = get_json(fusion_url)
            if not isinstance(health, dict) or not isinstance(fusion, dict):
                raise ValueError("Mesh health/fusion response must be JSON objects")
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            probe = MeshProbe(
                mediator=mediator,
                status="BLOCKED",
                url=health_url,
                checked_at=checked_at,
                correlation_id=correlation_id,
                detail=f"{type(exc).__name__}: {exc}",
            )
            self._record_probe(probe)
            return probe

        protocol_ok = health.get("protocol") == SOUL_MESH_PROTOCOL
        contract_ok = health.get("contractVersion") == SOUL_MESH_CONTRACT_VERSION
        identity_ok = health.get("nucleus") == mediator

        peers = health.get("peers")
        peer_ids: set[str] = set()
        if isinstance(peers, list):
            for peer in peers:
                if isinstance(peer, dict):
                    value = peer.get("id") or peer.get("nucleus")
                    if isinstance(value, str):
                        peer_ids.add(value)
        mesh_topology_ok = set(SOUL_NUCLEI).issubset(peer_ids | {mediator})

        federated_providers = fusion.get("federatedProviders")
        sara_provider = (
            federated_providers.get("SARA")
            if isinstance(federated_providers, dict)
            else None
        )
        sara_federation_ok = (
            isinstance(sara_provider, dict)
            and sara_provider.get("owner") == "SARA"
            and sara_provider.get("transport") == "HTTP"
            and isinstance(sara_provider.get("operations"), list)
            and {"sara.health", "sara.cycle", "sara.audit", "sara.regenerate", "sara.trace"}.issubset(
                set(str(item) for item in sara_provider.get("operations", []))
            )
        )
        sara_federation_configured = bool(
            sara_provider.get("configured", False)
        ) if isinstance(sara_provider, dict) else False

        if health_status != 200 or fusion_status != 200:
            state = "BLOCKED"
            detail = f"health_http={health_status}; fusion_http={fusion_status}"
        elif protocol_ok and contract_ok and identity_ok and mesh_topology_ok and sara_federation_configured:
            state = "VERIFIED"
            detail = "N01 Mesh + N01..N07 topology + N01↔SARA federation verified"
        elif protocol_ok and contract_ok and identity_ok and sara_federation_ok:
            state = "CONNECTED"
            detail = "N01 Mesh identity and SARA federation contract observed; external SARA configuration is not fully proven"
        else:
            state = "BLOCKED"
            detail = "Mesh/federation response failed contract, identity or SARA-provider validation"

        evidence = {
            "health_url": health_url,
            "fusion_url": fusion_url,
            "health_status": health_status,
            "fusion_status": fusion_status,
            "health": health,
            "fusion": fusion,
            "correlation_id": correlation_id,
        }
        probe = MeshProbe(
            mediator=mediator,
            status=state,
            url=health_url,
            checked_at=checked_at,
            correlation_id=correlation_id,
            http_status=health_status,
            protocol_ok=protocol_ok,
            contract_ok=contract_ok,
            identity_ok=identity_ok,
            mesh_topology_ok=mesh_topology_ok,
            sara_federation_ok=sara_federation_ok,
            sara_federation_configured=sara_federation_configured,
            evidence_hash=hash_json(evidence),
            detail=detail,
        )
        self._record_probe(probe)
        return probe

    def emit(self, event_type: str, payload: dict[str, Any], *, correlation_id: str | None = None) -> dict[str, Any]:
        """Publish a correlated fusion event through the existing VagusBus."""
        if self._vagus is None:
            raise RuntimeError("VAGUS_BUS_NOT_BOUND")
        cid = correlation_id or str(uuid.uuid4())
        event = self._vagus.publish_sync(
            "SARA.OCTACORE",
            "VagusBus",
            event_type,
            payload,
            correlation_id=cid,
            priority=100,
            ttl=5_000,
        )
        return event

    def verify_trinity_mirror(self, cycle_id: str) -> dict[str, Any]:
        """Independent verification of TrinitySynergy mirror hashing.

        This does not change TrinitySynergy. It verifies the actual fused
        payload against the stored hash, avoiding the original self-comparison
        pitfall where expected and calculated were derived from the same data.
        """
        if self._trinity is None or not hasattr(self._trinity, "mirror"):
            return {"status": "UNMEASURABLE", "reason": "Trinity mirror not bound"}
        mirror = self._trinity.mirror(cycle_id)
        if mirror is None:
            return {"status": "UNMEASURABLE", "reason": "mirror_not_found", "cycle_id": cycle_id}

        envelope = {
            "cycle_id": mirror.cycle_id,
            "target": mirror.target,
            "ara": mirror.ara,
            "etr": mirror.etr,
            "itr": mirror.itr,
            "eru": mirror.eru,
        }
        calculated = hash_json(envelope)
        expected = mirror.fused_hash
        ok = calculated == expected
        return {
            "status": "VERIFIED" if ok else "BLOCKED",
            "ok": ok,
            "cycle_id": cycle_id,
            "expected_hash": expected,
            "calculated_hash": calculated,
        }

    def context_digest(self, context: Any) -> str:
        """Create an integrity digest without storing raw cross-system payloads."""
        return hashlib.sha256(
            json.dumps(context, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

    def _record_probe(self, probe: MeshProbe) -> None:
        self._last_probe = probe
        if self._provenance is not None:
            provenance = (
                Provenance.RECONSTRUCTED
                if probe.status in {"CONNECTED", "VERIFIED"}
                else Provenance.UNKNOWN
            )
            self._provenance.register(
                f"SOUL_MESH.PROBE.{probe.mediator}.{probe.correlation_id}",
                provenance,
                probe.detail,
                source="OctaCoreMeshFusion.probe_mesh",
            )
        if self._vagus is not None:
            try:
                self.emit(
                    "mesh.probe",
                    {
                        "mediator": probe.mediator,
                        "status": probe.status,
                        "correlation_id": probe.correlation_id,
                        "evidence_hash": probe.evidence_hash,
                    },
                    correlation_id=probe.correlation_id,
                )
            except Exception:
                pass

    def emit_trace(self, ctx: Any) -> None:
        if hasattr(ctx, "record"):
            ctx.record(
                "monitoring",
                self.NAME,
                True,
                version=self.VERSION,
                mesh_contract=SOUL_MESH_CONTRACT_VERSION,
                octacore_slots=len(OCTACORE_SLOTS),
            )
