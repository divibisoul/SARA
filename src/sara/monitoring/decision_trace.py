"""SARA — Monitoramento: DecisionTrace v2.
Status: IMPLEMENTED (cadeia local thread-safe) | PENDING (IPFS).
"""
from __future__ import annotations
import threading
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.hashing import chain_hash
from sara.infra.clock import now_iso


@dataclass
class TraceEntry:
    index: int
    ts: str
    decision: dict
    prev_hash: str
    hash: str


class DecisionTrace:
    NAME = "DecisionTrace"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.MONITORING
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.MONITORING, CyclePhase.PERSISTENCE)

    def __init__(self) -> None:
        self._entries: list[TraceEntry] = []
        self._lock = threading.RLock()

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "ipfs_ready": self.is_ipfs_ready(),
        }

    def log(self, decision: dict) -> TraceEntry:
        with self._lock:
            prev = self._entries[-1].hash if self._entries else "GENESIS"
            h = chain_hash(prev, decision)
            entry = TraceEntry(
                index=len(self._entries),
                ts=now_iso(),
                decision=dict(decision),
                prev_hash=prev,
                hash=h,
            )
            self._entries.append(entry)
            return entry

    def verify(self) -> bool:
        with self._lock:
            prev = "GENESIS"
            for e in self._entries:
                expected = chain_hash(prev, e.decision)
                if expected != e.hash:
                    return False
                prev = e.hash
            return True

    def query(self, filters: Optional[dict] = None) -> list[TraceEntry]:
        with self._lock:
            if not filters:
                return list(self._entries)
            return [e for e in self._entries
                    if all(e.decision.get(k) == v for k, v in filters.items())]

    def is_ipfs_ready(self) -> bool:
        return bool(os.getenv("SARA_IPFS_API_URL", "").strip())

    def publish_to_ipfs(self, entry: TraceEntry) -> str:
        endpoint = os.getenv("SARA_IPFS_API_URL", "").strip()
        if not endpoint:
            raise NotImplementedError(
                "DecisionTrace.publish_to_ipfs requer SARA_IPFS_API_URL "
                "apontando para a API RPC HTTP de um nó/gateway IPFS real. "
                "Ativação: ver CANONICAL_ACTIVATION_PLAN.for_module('DecisionTrace')."
            )

        boundary = "----SARAIPFSBOUNDARY"
        payload = json.dumps({
            "index": entry.index,
            "ts": entry.ts,
            "decision": entry.decision,
            "prev_hash": entry.prev_hash,
            "hash": entry.hash,
        }, ensure_ascii=False).encode("utf-8")
        body = (
            f"--{boundary}\r\n"
            "Content-Disposition: form-data; name=\"file\"; filename=\"decision-trace.json\"\r\n"
            "Content-Type: application/json\r\n\r\n"
        ).encode() + payload + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            endpoint.rstrip("/") + "/api/v0/add",
            data=body,
            method="POST",
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "SARA-DecisionTrace/2.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(f"IPFS HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"IPFS transport error: {exc}") from exc

        try:
            response = json.loads(raw)
        except json.JSONDecodeError:
            # Kubo RPC normally returns newline-delimited JSON; parse the last object.
            response = json.loads(raw.strip().splitlines()[-1])
        cid = response.get("Hash") or response.get("cid")
        if not cid:
            raise RuntimeError("IPFS response sem Hash/cid")
        return str(cid)

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("monitoring", self.NAME, True,
                       total_entries=len(self._entries))