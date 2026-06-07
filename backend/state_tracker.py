"""Background State Tracker: merges transcript buffer into Redis JSON via OpenAI."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger("noah.state_tracker")

from dotenv import load_dotenv
from openai import OpenAI

from bpmn_redis import (
    append_buffer_line,
    clear_buffer,
    get_state_raw,
    read_buffer_lines,
    set_state_dict,
)
from bpmn_schema import (
    enforce_focus_integrity,
    enforce_phase_transitions,
    enforce_steps_on_state,
    normalize_state,
    parse_state_json,
    preserve_completed_processes,
)
from declined_answers import apply_declined_fields_from_transcript
from prompts import STATE_TRACKER_SYSTEM

load_dotenv(".env.local", override=True)


def _tracker_model() -> str:
    return os.getenv("STATE_TRACKER_MODEL", "gpt-4o-mini")


def _tracker_openai_timeout_s() -> float:
    raw = (os.getenv("STATE_TRACKER_OPENAI_TIMEOUT_S") or "60").strip()
    try:
        return max(10.0, float(raw))
    except ValueError:
        return 60.0


def run_state_tracker(*, room_name: str, allow_empty_buffer: bool = False) -> bool:
    """
    Read buffer + state, call OpenAI, write merged state, clear buffer on success.
    Returns True if state was written (including no-op when buffer empty and not allowed).
    """
    buf = read_buffer_lines(room_name)
    if not buf and not allow_empty_buffer:
        return False

    user_lines = [line for line in buf if line.get("role") == "user"]
    if not user_lines and not allow_empty_buffer:
        return False

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[SYSTEM] state_tracker: missing OPENAI_API_KEY, skipping")
        return False

    raw_state = get_state_raw(room_name)
    current = parse_state_json(raw_state)
    client = OpenAI(api_key=api_key, timeout=_tracker_openai_timeout_s())
    user_payload = {
        "current_json": current,
        "new_transcript_lines": buf,
    }

    model = _tracker_model()
    t0 = time.monotonic()
    logger.info(
        "OpenAI merge start room=%s model=%s buffer_lines=%s user_lines=%s",
        room_name,
        model,
        len(buf),
        len(user_lines),
    )
    try:
        completion = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[
                {"role": "system", "content": STATE_TRACKER_SYSTEM},
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                },
            ],
        )
    except Exception as e:
        logger.exception(
            "OpenAI merge failed room=%s after %.2fs: %s",
            room_name,
            time.monotonic() - t0,
            e,
        )
        return False

    text = (completion.choices[0].message.content or "").strip()
    try:
        merged = json.loads(text)
    except json.JSONDecodeError:
        logger.error(
            "model returned non-JSON room=%s after %.2fs",
            room_name,
            time.monotonic() - t0,
        )
        return False

    if not isinstance(merged, dict):
        return False

    normalized = normalize_state(merged)
    normalized = apply_declined_fields_from_transcript(buf, normalized)
    normalized = preserve_completed_processes(current, normalized)
    normalized = enforce_steps_on_state(normalized)
    normalized = enforce_phase_transitions(normalized)
    normalized = enforce_focus_integrity(normalized)
    set_state_dict(room_name, normalized)
    clear_buffer(room_name)
    logger.info("OpenAI merge done room=%s elapsed=%.2fs", room_name, time.monotonic() - t0)
    return True


def maybe_flush_tracker(*, room_name: str) -> None:
    """If buffer has lines, run tracker (e.g. on session end)."""
    if read_buffer_lines(room_name):
        run_state_tracker(room_name=room_name, allow_empty_buffer=False)


def flush_tracker_final(
    *,
    room_name: str,
    tail_transcript: list[dict[str, Any]] | None = None,
) -> None:
    """
    Final merge before DB persist: append any tail messages, then drain the buffer.
    """
    if tail_transcript:
        for line in tail_transcript:
            role = line.get("role")
            content = (line.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                append_buffer_line(room_name, role, content)

    max_passes = max(1, int(os.getenv("STATE_TRACKER_FINAL_MAX_PASSES", "3")))
    for _ in range(max_passes):
        if not read_buffer_lines(room_name):
            break
        run_state_tracker(room_name=room_name, allow_empty_buffer=False)
