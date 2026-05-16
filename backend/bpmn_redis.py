"""Redis keys for per-room BPMN discovery state and transcript buffer."""

from __future__ import annotations

import copy
import json
import os
from typing import Any

import redis

from hobby_schema import DEFAULT_HOBBY_STATE, parse_state_json, state_to_json

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _client() -> redis.Redis:
    return redis.from_url(_REDIS_URL, decode_responses=True)


def _ttl_s() -> int:
    return int(os.getenv("BPMN_REDIS_TTL_S", str(48 * 3600)))


def state_key(room_name: str) -> str:
    return f"lk:bpmn:state:{room_name}"


def buf_key(room_name: str) -> str:
    return f"lk:bpmn:buf:{room_name}"


def ensure_default_state(room_name: str) -> None:
    r = _client()
    sk = state_key(room_name)
    bk = buf_key(room_name)
    if not r.exists(sk):
        r.set(sk, state_to_json(copy.deepcopy(DEFAULT_HOBBY_STATE)))
    ttl = _ttl_s()
    r.expire(sk, ttl)
    if r.exists(bk):
        r.expire(bk, ttl)


def get_state_raw(room_name: str) -> str | None:
    r = _client()
    raw = r.get(state_key(room_name))
    return raw if isinstance(raw, str) else None


def get_state_dict(room_name: str) -> dict[str, Any]:
    return parse_state_json(get_state_raw(room_name))


def set_state_dict(room_name: str, state: dict[str, Any]) -> None:
    r = _client()
    sk = state_key(room_name)
    r.set(sk, state_to_json(state))
    r.expire(sk, _ttl_s())


def append_buffer_line(room_name: str, role: str, content: str) -> None:
    line = json.dumps({"role": role, "content": content}, ensure_ascii=False)
    r = _client()
    bk = buf_key(room_name)
    r.rpush(bk, line)
    r.expire(bk, _ttl_s())


def read_buffer_lines(room_name: str) -> list[dict[str, Any]]:
    r = _client()
    raw_lines = r.lrange(buf_key(room_name), 0, -1)
    out: list[dict[str, Any]] = []
    if not raw_lines:
        return out
    for raw in raw_lines:
        if not isinstance(raw, str):
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("role") in ("user", "assistant"):
            out.append(obj)
    return out


def clear_buffer(room_name: str) -> None:
    _client().delete(buf_key(room_name))


def buffer_length(room_name: str) -> int:
    return int(_client().llen(buf_key(room_name)))


def delete_room_discovery_keys(room_name: str) -> None:
    """Remove state + transcript buffer for a room (after DB persist or session end)."""
    _client().delete(state_key(room_name), buf_key(room_name))


def list_discovery_state_room_names() -> list[str]:
    """Room names that currently have a state key in Redis (SCAN, safe for large keyspaces)."""
    r = _client()
    prefix = "lk:bpmn:state:"
    pattern = f"{prefix}*"
    names: list[str] = []
    for key in r.scan_iter(match=pattern, count=200):
        if isinstance(key, bytes):
            key = key.decode("utf-8", errors="replace")
        if isinstance(key, str) and key.startswith(prefix):
            names.append(key[len(prefix) :])
    names.sort()
    return names
