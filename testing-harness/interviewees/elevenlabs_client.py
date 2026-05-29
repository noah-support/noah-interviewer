from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import AsyncConversation

from interviewees.core.end_signal import contains_sentinel, strip_sentinel
from interviewees.core.persona import Persona
from interviewees.core.session import InterviewSession
from interviewees.core.transcript import (
    Transcript,
    default_transcript_dir,
    transcript_filename,
    write_transcript,
)


@dataclass
class ElevenLabsConfig:
    api_key: str
    agent_id: str


def _load_config() -> ElevenLabsConfig:
    api_key = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
    agent_id = (os.environ.get("ELEVENLABS_AGENT_ID") or "").strip()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")
    if not agent_id:
        raise RuntimeError("ELEVENLABS_AGENT_ID is not set")
    return ElevenLabsConfig(api_key=api_key, agent_id=agent_id)


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

    def on_agent_response(text: str) -> None:
        if text is None:
            return
        incoming.put_nowait(str(text))

    conv = AsyncConversation(
        client=client,
        agent_id=cfg.agent_id,
        requires_auth=True,
        audio_interface=None,
        callback_agent_response=on_agent_response,
    )

    await conv.start_session()

    try:
        while True:
            interviewer_text = await incoming.get()
            # Sentinel check happens before LLM.
            raw = interviewer_text
            cleaned = strip_sentinel(raw)
            if cleaned:
                # record as interviewer
                pass

            reply, should_disconnect = session.handle_interviewer_message(raw)
            if reply:
                await conv.send_user_message(reply)

            if should_disconnect:
                ended_by = "sentinel" if contains_sentinel(raw) else "turn_cap"
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

