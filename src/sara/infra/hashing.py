"""SARA — Infra: hashing determinístico.
Status: IMPLEMENTED
"""
from __future__ import annotations
import hashlib
import json
from typing import Any


def hash_json(data: Any) -> str:
    payload = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def short_hash(data: Any, length: int = 16) -> str:
    return hash_json(data)[:length]


def chain_hash(prev_hash: str, data: Any) -> str:
    payload = (prev_hash + json.dumps(data, sort_keys=True, default=str)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()