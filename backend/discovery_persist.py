"""Persist Redis discovery JSON to Postgres (Interview.discovery_state_json)."""

from __future__ import annotations

import json

from database import db
from models import Interview

from bpmn_redis import get_state_raw


def persist_discovery_state_to_db(*, interview_id: int, room_name: str) -> bool:
    """Persist Redis JSON to the interview row. No-op if Redis has no state (avoids wiping DB after cleanup)."""
    raw = get_state_raw(room_name)
    if not raw or not raw.strip():
        return False

    payload = raw

    db.connect(reuse_if_open=True)
    try:
        interview = Interview.get_or_none(Interview.id == interview_id)
        if not interview:
            return False
        interview.discovery_state_json = payload
        interview.save()
        return True
    finally:
        db.close()


def persist_discovery_state_from_json(*, interview_id: int, state: dict) -> None:
    payload = json.dumps(state, ensure_ascii=False)
    db.connect(reuse_if_open=True)
    try:
        interview = Interview.get_or_none(Interview.id == interview_id)
        if not interview:
            return
        interview.discovery_state_json = payload
        interview.save()
    finally:
        db.close()
