from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from livekit import api, rtc

from interviewees.core.end_signal import ended_by_for_disconnect
from interviewees.core.persona import Persona
from interviewees.core.session import InterviewSession
from interviewees.core.transcript import (
    Transcript,
    default_transcript_dir,
    transcript_filename,
    write_transcript,
)
from interviewees.core.timeouts import interviewee_reply_delay_s, interviewer_idle_timeout_s
from interviewees.env import load_harness_env
from interviewees.noah_api import InterviewRecord, LiveKitSession, NoahApiClient

logger = logging.getLogger("harness.livekit")

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


@dataclass
class _TranscriptionAssembler:
    """
    Assemble agent transcription text streams.

    LiveKit delta mode sets ``lk.transcription_final=false`` on stream open; the
    ``true`` flag is sent on writer close and may not appear on ``reader.info``.
    Each ``lk.transcription`` handler invocation reads the full stream, so we
    flush when ``stream_ended`` is True even if ``is_final`` is False.
    """

    parts: dict[str, list[str]] = field(default_factory=dict)

    def ingest(
        self,
        *,
        segment_id: str,
        text: str,
        is_final: bool | None,
        stream_ended: bool = False,
    ) -> str | None:
        if not text and not segment_id:
            return None

        if not segment_id:
            return text.strip() or None

        bucket = self.parts.setdefault(segment_id, [])
        if text:
            bucket.append(text)

        if is_final is False and not stream_ended:
            logger.debug(
                "transcription partial segment_id=%s accumulated_chars=%s",
                segment_id,
                sum(len(p) for p in bucket),
            )
            return None

        merged = "".join(bucket).strip()
        self.parts.pop(segment_id, None)
        if merged:
            logger.debug(
                "transcription complete segment_id=%s chars=%s final_attr=%s stream_ended=%s",
                segment_id,
                len(merged),
                is_final,
                stream_ended,
            )
        return merged or None


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def _load_connection_from_env() -> LiveKitConnection:
    load_harness_env()
    url = _env("LIVEKIT_URL")
    room = _env("LIVEKIT_ROOM")
    identity = _env("LIVEKIT_IDENTITY") or "harness-interviewee"
    token = _env("LIVEKIT_TOKEN")

    if not url:
        raise RuntimeError("LIVEKIT_URL is not set")
    if not room:
        raise RuntimeError(
            "LIVEKIT_ROOM is not set. For Noah runs, use `runner.py interview --interviewer noah` "
            "(auto-provisions via the Noah API) or set LIVEKIT_ROOM in testing-harness/.env."
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
    load_harness_env()
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

    logger.info(
        "connecting room=%s identity=%s url=%s",
        connection.room,
        connection.identity,
        connection.url,
    )
    room = rtc.Room()
    await room.connect(connection.url, connection.token)
    logger.info("connected room=%s", connection.room)

    session = InterviewSession(
        persona,
        interviewer="livekit",
        mode=mode,
        openai_model=openai_model,
        verbose=verbose,
    )

    incoming: asyncio.Queue[str] = asyncio.Queue()
    identity = connection.identity
    assembler = _TranscriptionAssembler()
    exchange_idx = 0

    def on_text_received(reader: rtc.TextStreamReader, participant_identity: str) -> None:
        async def _consume() -> None:
            if participant_identity == identity:
                return

            attrs: dict[str, str] = dict(reader.info.attributes or {})
            segment_id = (attrs.get(ATTRIBUTE_SEGMENT_ID) or "").strip()
            is_final = _parse_bool(attrs.get(ATTRIBUTE_FINAL))
            buf: list[str] = []
            async for chunk in reader:
                if chunk:
                    buf.append(str(chunk))

            chunk_text = "".join(buf)
            merged = assembler.ingest(
                segment_id=segment_id,
                text=chunk_text,
                is_final=is_final,
                stream_ended=True,
            )
            if not merged:
                logger.warning(
                    "ignored empty lk.transcription from=%s segment_id=%s final_attr=%s",
                    participant_identity,
                    segment_id or "(none)",
                    is_final,
                )
                return

            logger.info(
                "recv lk.transcription from=%s final_attr=%s stream_ended=True chars=%s preview=%r",
                participant_identity,
                is_final,
                len(merged),
                merged.replace("\n", " ")[:120],
            )
            await incoming.put(merged)

        asyncio.create_task(_consume())

    room.register_text_stream_handler(topic=TOPIC_TRANSCRIPTION, handler=on_text_received)

    ended_by = "manual"
    last_interviewer_text = ""
    idle_timeout_s = interviewer_idle_timeout_s()
    reply_delay_s = interviewee_reply_delay_s()

    try:
        while True:
            exchange_idx += 1
            wait_t0 = time.monotonic()
            logger.info(
                "waiting interviewer message #%s timeout=%.0fs",
                exchange_idx,
                idle_timeout_s,
            )
            try:
                interviewer_text = await asyncio.wait_for(
                    incoming.get(), timeout=idle_timeout_s
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "idle timeout after %.0fs (no lk.transcription since last message); "
                    "last_interviewer_preview=%r",
                    idle_timeout_s,
                    last_interviewer_text.replace("\n", " ")[:120],
                )
                ended_by = "idle_timeout"
                break

            wait_elapsed = time.monotonic() - wait_t0
            last_interviewer_text = interviewer_text
            logger.info(
                "got interviewer #%s wait_elapsed=%.2fs chars=%s",
                exchange_idx,
                wait_elapsed,
                len(interviewer_text),
            )

            if reply_delay_s > 0:
                logger.info(
                    "pacing %.1fs before interviewee reply #%s (state tracker / rate limits)",
                    reply_delay_s,
                    exchange_idx,
                )
                await asyncio.sleep(reply_delay_s)

            llm_t0 = time.monotonic()
            reply, should_disconnect = await asyncio.to_thread(
                session.handle_interviewer_message, interviewer_text
            )
            logger.info(
                "interviewee reply generated #%s elapsed=%.2fs should_disconnect=%s "
                "reply_chars=%s",
                exchange_idx,
                time.monotonic() - llm_t0,
                should_disconnect,
                len(reply or ""),
            )

            if reply:
                send_t0 = time.monotonic()
                await room.local_participant.send_text(reply, topic=TOPIC_CHAT)
                logger.info(
                    "sent lk.chat #%s elapsed=%.2fs chars=%s preview=%r",
                    exchange_idx,
                    time.monotonic() - send_t0,
                    len(reply),
                    reply.replace("\n", " ")[:120],
                )
            else:
                logger.warning("no interviewee reply to send for exchange #%s", exchange_idx)

            if should_disconnect:
                ended_by = ended_by_for_disconnect(interviewer_text)
                logger.info("disconnecting ended_by=%s", ended_by)
                break
    except Exception:
        ended_by = "error"
        logger.exception("interview loop failed room=%s", connection.room)
        raise
    finally:
        try:
            await room.disconnect()
            logger.info("disconnected room=%s", connection.room)
        except Exception:
            logger.exception("room disconnect failed room=%s", connection.room)

    transcript = session.finish(ended_by=ended_by)
    out_dir = default_transcript_dir(
        transcript.project, smoke=(mode == "smoke"), override=transcript_dir
    )
    out_path = out_dir / transcript_filename(transcript.subject_label, "livekit")
    write_transcript(out_path, transcript)
    logger.info(
        "transcript written path=%s ended_by=%s turn_count=%s",
        out_path,
        ended_by,
        transcript.turn_count,
    )

    db_record: InterviewRecord | None = None
    end_resp: dict[str, Any] | None = None
    interview_id = livekit_session.interview_id if livekit_session else None
    room_name = connection.room

    if noah_api is not None and interview_id is not None and room_name:
        logger.info("calling /end interview_id=%s room=%s", interview_id, room_name)
        end_resp = await asyncio.to_thread(
            noah_api.end_interview, interview_id, room_name
        )
        logger.info("waiting DB persist interview_id=%s timeout=%.0fs", interview_id, persist_wait_timeout_s)
        db_record = await asyncio.to_thread(
            noah_api.wait_for_persisted,
            interview_id,
            timeout_s=persist_wait_timeout_s,
        )
        logger.info(
            "DB persist done interview_id=%s status=%s",
            interview_id,
            db_record.status if db_record else None,
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
