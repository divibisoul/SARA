from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

UPSTREAM_COMMIT = "abb81c88e1f738a8117d8293530fbc31a5ef8fd9"

@dataclass(frozen=True)
class Mem0Config:
    base_url: str
    api_key: str
    user_id: str

def load_config() -> Mem0Config:
    base = os.getenv("SARA_MEM0_URL", "https://api.mem0.ai").strip().rstrip("/")
    key = os.getenv("SARA_MEM0_API_KEY", "").strip()
    user = os.getenv("SARA_MEM0_USER_ID", "sara").strip() or "sara"
    return Mem0Config(base, key, user)

def configured() -> bool:
    config = load_config()
    return bool(config.base_url and config.api_key)

def _request(method: str, path: str, body: dict | None = None) -> dict:
    config = load_config()
    if not config.api_key:
        raise RuntimeError("MEM0_API_KEY_NOT_CONFIGURED")
    headers = {
        "Authorization": f"Token {config.api_key}",
        "Accept": "application/json",
        "Mem0-User-ID": config.user_id,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = Request(config.base_url + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode()
            return json.loads(raw or "{}")
    except HTTPError as exc:
        raise RuntimeError(f"MEM0_HTTP_{exc.code}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("MEM0_UNREACHABLE") from exc

def status() -> dict:
    config = load_config()
    if not config.api_key:
        return {"provider": "mem0ai/mem0", "upstreamCommit": UPSTREAM_COMMIT, "state": "BLOCKED", "code": "MEM0_API_KEY_NOT_CONFIGURED"}
    try:
        _request("GET", "/v1/ping/")
        return {"provider": "mem0ai/mem0", "upstreamCommit": UPSTREAM_COMMIT, "state": "LIVE"}
    except RuntimeError as exc:
        return {"provider": "mem0ai/mem0", "upstreamCommit": UPSTREAM_COMMIT, "state": "BLOCKED", "code": str(exc)}

def add(messages, user_id: str | None = None, metadata: dict | None = None) -> dict:
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    if not isinstance(messages, list) or not messages:
        raise ValueError("MEM0_MESSAGES_REQUIRED")
    body = {"messages": messages, "user_id": user_id or load_config().user_id}
    if metadata is not None:
        body["metadata"] = metadata
    return _request("POST", "/v3/memories/add/", body)

def search(query: str, user_id: str | None = None, top_k: int | None = None, filters: dict | None = None) -> dict:
    if not str(query).strip():
        raise ValueError("MEM0_QUERY_REQUIRED")
    body = {"query": str(query).strip(), "user_id": user_id or load_config().user_id}
    if top_k is not None:
        body["top_k"] = max(1, min(100, int(top_k)))
    if filters is not None:
        body["filters"] = filters
    return _request("POST", "/v3/memories/search/", body)

def get_all(user_id: str | None = None, page: int | None = None, page_size: int | None = None, filters: dict | None = None) -> dict:
    body = {"user_id": user_id or load_config().user_id}
    if filters is not None:
        body["filters"] = filters
    params = []
    if page is not None:
        params.append("page=" + quote(str(page)))
    if page_size is not None:
        params.append("page_size=" + quote(str(page_size)))
    path = "/v3/memories/" + (("?" + "&".join(params)) if params else "")
    return _request("POST", path, body)
