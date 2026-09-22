"""SARA — Infra: relógio.
Status: IMPLEMENTED
"""
from __future__ import annotations
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)