from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

from livekit import api, rtc

from interviewees.core.end_signal import contains_sentinel
from interviewees.core.persona import Persona
from interviewees.core.session import InterviewSession
from interviewees.core.transcript import (
    Transcript,
    default_transcript_dir,
    transcript_filename,
    write_transcript,
)
from interviewees.noah_api import InterviewRecord, LiveKitSession, NoahApiClient

TOPIC_CHAT = "lk.chat"
TOPIC_TRANSCRIPTION = "lk.transcription"

ATTRIBUTE_SEGMENT_ID = "lk.segment_id"
ATTRIBUTE_TRACK_ID = "lk.transcribed_track_id"
ATTRIBUTE_FINAL = "lk.transcription_final"


@dataclass(frozen=True)
class LiveKitConnection:
    url: str
    room: str
    identity: str
    token: str


@dataclass
class LiveKitInterviewResult:
    transcript: Transcript
    transcript_path: str
    ended_by: str
    interview_id: int | None = None
    room: str | None = None
    db_record: InterviewRecord | None = None
    end_api_response: dict[str, Any] | None = None


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def _load_connection_from_env() -> LiveKitConnection:
    url = _env("LIVEKIT_URL")
    room = _env("LIVEKIT_ROOM")
    identity = _env("LIVEKIT_IDENTITY") or "harness-interviewee"
    token = _env("LIVEKIT_TOKEN")

    if not url:
        raise RuntimeError("LIVEKIT_URL is not set")
    if not room:
        raise RuntimeError(
            "LIVEKIT_ROOM is not set. Use project mode (runner project) for automatic "
            "token/room via the Noah API, or set LIVEKIT_ROOM manually."
        )

    if not token:
        api_key = _env("LIVEKIT_API_KEY")
        api_secret = _env("LIVEKIT_API_SECRET")
        if not api_key or not api_secret:
            raise RuntimeError(
                "Provide LIVEKIT_TOKEN, or set LIVEKIT_API_KEY and LIVEKIT_API_SECRET."
            )
        token = (
            api.AccessToken(api_key, api_secret)
            .with_identity(identity)
            .with_name(identity)
            .with_grants(api.VideoGrants(room_join=True, room=room))
            .to_jwt()
        )

    return LiveKitConnection(url=url, room=room, identity=identity, token=token)


def connection_from_session(lk: LiveKitSession, *, url: str | None = None) -> LiveKitConnection:
    livekit_url = (url or _env("LIVEKIT_URL")).strip()
    if not livekit_url:
        raise RuntimeError("LIVEKIT_URL is not set")
    return LiveKitConnection(
        url=livekit_url,
        room=lk.room,
        identity=lk.username,
        token=lk.token,
    )


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    v = value.strip().lower()
    if v in ("true", "1"):
        return True
    if v in ("false", "0"):
        return False
    return None


async def run_interview(
    persona: Persona,
    *,
    mode: str,
    openai_model: str,
    transcript_dir: str | None,
    verbose: bool,
    connection: LiveKitConnection | None = None,
    livekit_session: LiveKitSession | None = None,
    noah_api: NoahApiClient | None = None,
    persist_wait_timeout_s: float = 60.0,
) -> LiveKitInterviewResult:
    """
    Run a text interview over LiveKit text streams.

    When ``livekit_session`` and ``noah_api`` are provided, completes the human-like
  lifecycle: join → converse → disconnect → POST /end → wait for DB content/summary/state.
    """
    if connection is None and livekit_session is not None:
        connection = connection_from_session(livekit_session)
    if connection is None:
        connection = _load_connection_from_env()

    room = rtc.Room()
    await room.connect(connection.url, connection.token)

    session = InterviewSession(
        persona,
        interviewer="livekit",
        mode=mode,
        openai_model=openai_model,
        verbose=verbose,
    )

    incoming: asyncio.Queue[str] = asyncio.Queue()
    identity = connection.identity

    def on_text_received(reader: rtc.TextStreamReader, participant_identity: str) -> None:
        async def _consume() -> None:
            if participant_identity == identity:
                return

            attrs: dict[str, str] = dict(reader.info.attributes or {})
            buf: list[str] = []
            async for chunk in reader:
                if chunk:
                    buf.append(str(chunk))

            text = "".join(buf).strip()
            if not text:
                return
            _ = _parse_bool(attrs.get(ATTRIBUTE_FINAL))
            await incoming.put(text)

        asyncio.create_task(_consume())

    room.register_text_stream_handler(topic=TOPIC_TRANSCRIPTION, handler=on_text_received)

    ended_by = "manual"
    last_interviewer_text = ""

    try:
        while True:
            interviewer_text = await incoming.get()
            last_interviewer_text = interviewer_text
            reply, should_disconnect = session.handle_interviewer_message(interviewer_text)
            if reply:
                await room.local_participant.send_text(reply, topic=TOPIC_CHAT)
            if should_disconnect:
                ended_by = (
                    "sentinel"
                    if contains_sentinel(interviewer_text)
                    else "turn_cap"
                )
                break
    except Exception:
        ended_by = "error"
        raise
    finally:
        try:
            await room.disconnect()
        except Exception:
            pass

    transcript = session.finish(ended_by=ended_by)
    out_dir = default_transcript_dir(
        transcript.project, smoke=(mode == "smoke"), override=transcript_dir
    )
    out_path = out_dir / transcript_filename(transcript.subject_label, "livekit")
    write_transcript(out_path, transcript)

    db_record: InterviewRecord | None = None
    end_resp: dict[str, Any] | None = None
    interview_id = livekit_session.interview_id if livekit_session else None
    room_name = connection.room

    if noah_api is not None and interview_id is not None and room_name:
        end_resp = await asyncio.to_thread(
            noah_api.end_interview, interview_id, room_name
        )
        db_record = await asyncio.to_thread(
            noah_api.wait_for_persisted,
            interview_id,
            timeout_s=persist_wait_timeout_s,
        )

    return LiveKitInterviewResult(
        transcript=transcript,
        transcript_path=str(out_path),
        ended_by=ended_by,
        interview_id=interview_id,
        room=room_name,
        db_record=db_record,
        end_api_response=end_resp,
    )
