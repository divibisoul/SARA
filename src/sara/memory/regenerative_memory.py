"""SARA — Memória: RegenerativeMemory (versionada).
Status: IMPLEMENTED
"""
from __future__ import annotations
import copy
import json
import os
import threading
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any, Optional
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.hashing import short_hash
from sara.infra.clock import now_iso


@dataclass
class VersionRecord:
    id: int
    label: str
    state: dict
    ts: str
    integrity: str


class RegenerativeMemory:
    NAME = "RegenerativeMemory"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.MEMORY
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.PERSISTENCE,)

    def __init__(self, persist_path: str | None = None) -> None:
        self._versions: list[VersionRecord] = []
        self._counter = 0
        self._persist_path = (persist_path or os.getenv("SARA_MEMORY_PERSIST_PATH", "")).strip() or None
        self._lock = threading.RLock()

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "versions": len(self._versions),
            "latest_integrity": self._versions[-1].integrity if self._versions else None,
            "integrity_valid": self.verify_integrity(),
            "persistence_enabled": self._persist_path is not None,
            "persistence_path": self._persist_path,
        }

    def store(self, state: dict, label: str = "") -> VersionRecord:
        with self._lock:
            self._counter += 1
            integrity = short_hash(state)
            v = VersionRecord(
                id=self._counter,
                label=label,
                state=copy.deepcopy(state),
                ts=now_iso(),
                integrity=integrity,
            )
            self._versions.append(v)
            return v

    def get(self, version_id: int) -> Optional[VersionRecord]:
        for v in self._versions:
            if v.id == version_id:
                return v
        return None

    def latest(self) -> Optional[VersionRecord]:
        return self._versions[-1] if self._versions else None

    def diff(self, v1_id: int, v2_id: int) -> dict:
        v1 = self.get(v1_id)
        v2 = self.get(v2_id)
        if not v1 or not v2:
            return {"error": "version_not_found"}
        paths1 = self._flatten(v1.state)
        paths2 = self._flatten(v2.state)
        keys1, keys2 = set(paths1), set(paths2)
        changed = sorted(k for k in keys1 & keys2 if paths1[k] != paths2[k])
        return {
            "same_integrity": v1.integrity == v2.integrity,
            "v1_len": len(str(v1.state)),
            "v2_len": len(str(v2.state)),
            "lost": sorted(keys1 - keys2),
            "added": sorted(keys2 - keys1),
            "changed": changed,
            "kept": sorted((keys1 & keys2) - set(changed)),
        }

    @staticmethod
    def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
        out: dict[str, Any] = {}
        if isinstance(obj, dict):
            for key, value in obj.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                if isinstance(value, (dict, list)):
                    out.update(RegenerativeMemory._flatten(value, path))
                else:
                    out[path] = value
        elif isinstance(obj, list):
            for idx, value in enumerate(obj):
                path = f"{prefix}[{idx}]"
                if isinstance(value, (dict, list)):
                    out.update(RegenerativeMemory._flatten(value, path))
                else:
                    out[path] = value
        else:
            out[prefix or "$"] = obj
        return out

    def verify_integrity(self, version_id: int | None = None) -> bool:
        target = self.get(version_id) if version_id is not None else self.latest()
        if target is None:
            return False
        return short_hash(target.state) == target.integrity

    def trail(self) -> list[VersionRecord]:
        return list(self._versions)

    def persist(self, path: str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            payload = [asdict(v) for v in self._versions]
        tmp = target.with_name(target.name + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, target)

    def persist_if_configured(self) -> bool:
        if not self._persist_path:
            return False
        self.persist(self._persist_path)
        return True

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        loaded = [VersionRecord(**p) for p in payload]
        if any(not isinstance(v.state, dict) or short_hash(v.state) != v.integrity for v in loaded):
            raise ValueError("REGN_MEMORY_INTEGRITY_FAILED")
        with self._lock:
            self._versions = loaded
            self._counter = max((v.id for v in self._versions), default=0)

    def load_if_configured(self) -> bool:
        if not self._persist_path or not Path(self._persist_path).exists():
            return False
        self.load(self._persist_path)
        return True

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("persistence", self.NAME, True,
                       total_versions=len(self._versions))