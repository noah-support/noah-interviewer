from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass

from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import (
    AgentChatResponsePartType,
    AsyncConversation,
    ConversationInitiationData,
)

from interviewees.core.end_signal import ended_by_for_disconnect
from interviewees.core.persona import Persona
from interviewees.core.session import InterviewSession
from interviewees.core.timeouts import interviewee_reply_delay_s, interviewer_idle_timeout_s
from interviewees.core.transcript import (
    Transcript,
    default_transcript_dir,
    transcript_filename,
    write_transcript,
)
from interviewees.env import load_harness_env, require_env

# ElevenLabs closes the session if no user message arrives within ~60s.
_KICK_USER_MESSAGE = "Hello, I'm ready for the interview."
_WS_CONNECT_TIMEOUT_S = 30.0
_FIRST_AGENT_REPLY_TIMEOUT_S = 8.0


@dataclass
class ElevenLabsConfig:
    api_key: str
    agent_id: str


def _load_config() -> ElevenLabsConfig:
    return ElevenLabsConfig(
        api_key=require_env("ELEVENLABS_API_KEY"),
        agent_id=require_env("ELEVENLABS_AGENT_ID"),
    )


def _dynamic_variables_for_persona(persona: Persona) -> dict[str, str]:
    """
    ElevenLabs agents often require {{name}} (and other vars) at session start.

    Defaults from persona.json; merge ``ELEVENLABS_DYNAMIC_VARIABLES_JSON`` from .env
    for extra keys your hosted agent expects.
    """
    load_harness_env()
    variables: dict[str, str] = {
        "name": persona.name,
        "role": persona.role,
    }
    raw = (os.environ.get("ELEVENLABS_DYNAMIC_VARIABLES_JSON") or "").strip()
    if raw:
        extra = json.loads(raw)
        if not isinstance(extra, dict):
            raise ValueError(
                "ELEVENLABS_DYNAMIC_VARIABLES_JSON must be a JSON object, e.g. "
                '{"name": "Alex"}'
            )
        for key, value in extra.items():
            if value is not None:
                variables[str(key)] = str(value)
    return variables


async def _wait_for_websocket(conv: AsyncConversation, *, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    while conv._ws is None:
        if conv._should_stop.is_set():
            raise RuntimeError("ElevenLabs session ended before websocket connected")
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"ElevenLabs websocket did not connect within {timeout_s:.0f}s"
            )
        await asyncio.sleep(0.05)


async def _recv_agent_message(
    incoming: asyncio.Queue[str],
    *,
    timeout_s: float | None,
) -> str:
    if timeout_s is None:
        return await incoming.get()
    return await asyncio.wait_for(incoming.get(), timeout=timeout_s)


async def run_interview(
    persona: Persona,
    *,
    mode: str,
    openai_model: str,
    transcript_dir: str | None,
    verbose: bool,
) -> tuple[Transcript, str]:
    """
    Run a single text-only interview against a hosted ElevenLabs Conversational AI agent.

    Returns (transcript, written_path).
    """
    cfg = _load_config()
    client = ElevenLabs(api_key=cfg.api_key)

    session = InterviewSession(
        persona,
        interviewer="elevenlabs",
        mode=mode,
        openai_model=openai_model,
        verbose=verbose,
    )

    incoming: asyncio.Queue[str] = asyncio.Queue()
    ended_by: str = "manual"
    stream_parts: list[str] = []

    def _enqueue_agent_text(text: str) -> None:
        cleaned = (text or "").strip()
        if cleaned:
            incoming.put_nowait(cleaned)

    # Text-only ConvAI delivers each reply via chat parts; the full-response callback
    # would enqueue the same text again (doubling turns in the transcript).
    async def on_agent_chat_response_part(
        text: str, part_type: AgentChatResponsePartType
    ) -> None:
        if part_type == AgentChatResponsePartType.START:
            stream_parts.clear()
            return
        if part_type == AgentChatResponsePartType.DELTA:
            if text:
                stream_parts.append(text)
            return
        if part_type == AgentChatResponsePartType.STOP:
            _enqueue_agent_text("".join(stream_parts))

    el_config = ConversationInitiationData(
        conversation_config_override={"text_only": True},
        dynamic_variables=_dynamic_variables_for_persona(persona),
    )

    conv = AsyncConversation(
        client=client,
        agent_id=cfg.agent_id,
        requires_auth=True,
        audio_interface=None,
        config=el_config,
        callback_agent_chat_response_part=on_agent_chat_response_part,
    )

    await conv.start_session()
    await _wait_for_websocket(conv, timeout_s=_WS_CONNECT_TIMEOUT_S)

    idle_timeout_s = interviewer_idle_timeout_s()
    reply_delay_s = interviewee_reply_delay_s()

    try:
        try:
            interviewer_text = await _recv_agent_message(
                incoming, timeout_s=_FIRST_AGENT_REPLY_TIMEOUT_S
            )
        except asyncio.TimeoutError:
            await conv.send_user_message(_KICK_USER_MESSAGE)
            interviewer_text = await _recv_agent_message(
                incoming, timeout_s=idle_timeout_s
            )

        while True:
            raw = interviewer_text
            if reply_delay_s > 0:
                await asyncio.sleep(reply_delay_s)
            # OpenAI is sync; run off the event loop so ElevenLabs WS can answer pings
            # and the ~60s idle timeout is not hit while generating a reply.
            reply, should_disconnect = await asyncio.to_thread(
                session.handle_interviewer_message, raw
            )
            if reply:
                await conv.send_user_message(reply)

            if should_disconnect:
                ended_by = ended_by_for_disconnect(raw)
                break

            try:
                interviewer_text = await _recv_agent_message(
                    incoming, timeout_s=idle_timeout_s
                )
            except asyncio.TimeoutError:
                ended_by = "idle_timeout"
                break
    finally:
        try:
            await conv.end_session()
        except Exception:
            ended_by = "error" if ended_by == "manual" else ended_by

    transcript = session.finish(ended_by=ended_by)
    out_dir = default_transcript_dir(
        transcript.project, smoke=(mode == "smoke"), override=transcript_dir
    )
    out_path = out_dir / transcript_filename(transcript.subject_label, "elevenlabs")
    write_transcript(out_path, transcript)
    return transcript, str(out_path)
