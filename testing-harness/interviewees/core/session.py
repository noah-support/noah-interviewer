"""Shared interview turn handling for transport clients."""

from __future__ import annotations

import logging

from interviewees.core.end_signal import contains_sentinel, strip_sentinel
from interviewees.core.llm import IntervieweeLLM
from interviewees.core.persona import Persona, assemble_system_prompt
from interviewees.core.transcript import TranscriptRecorder

logger = logging.getLogger(__name__)

CLOSING_ON_CAP = (
    "Thanks for your time today. I think we've covered everything on my end."
)


def turn_cap_for_mode(mode: str) -> int:
    return 10 if mode == "smoke" else 80


class InterviewSession:
    """Orchestrates LLM replies, sentinel handling, and transcript recording."""

    def __init__(
        self,
        persona: Persona,
        *,
        interviewer: str,
        mode: str,
        openai_model: str,
        verbose: bool = False,
    ) -> None:
        self.persona = persona
        self.mode = mode
        self.verbose = verbose
        self.turn_cap = turn_cap_for_mode(mode)
        self.system_prompt = assemble_system_prompt(persona)
        self.llm = IntervieweeLLM(model=openai_model)
        self.recorder = TranscriptRecorder(
            persona_id=persona.id,
            project=persona.project,
            subject_label=persona.subject_label,
            interviewer=interviewer,
        )
        self._history: list[dict[str, str]] = []
        self._exchange_count = 0

    def _log_turn(self, role: str, text: str) -> None:
        if self.verbose:
            print(f"[{role}] {text}", flush=True)

    def handle_interviewer_message(
        self,
        raw_text: str,
    ) -> tuple[str | None, bool]:
        """
        Process an interviewer turn.

        Returns (interviewee_reply_or_none, should_disconnect).
        ``None`` reply means disconnect without sending (only on turn cap before reply).
        """
        cleaned = strip_sentinel(raw_text)
        had_sentinel = contains_sentinel(raw_text)

        if cleaned:
            self.recorder.add_interviewer(cleaned)
            self._log_turn("interviewer", cleaned)

        if had_sentinel:
            reply = self._generate_reply(cleaned or "Thanks, goodbye.")
            self.recorder.add_interviewee(reply)
            self._log_turn("interviewee", reply)
            return reply, True

        self._exchange_count += 1
        if self._exchange_count > self.turn_cap:
            logger.warning(
                "Turn count exceeded %s without sentinel; closing interview.",
                self.turn_cap,
            )
            reply = CLOSING_ON_CAP
            self.recorder.add_interviewee(reply)
            self._log_turn("interviewee", reply)
            return reply, True

        reply = self._generate_reply(cleaned)
        self.recorder.add_interviewee(reply)
        self._log_turn("interviewee", reply)
        return reply, False

    def _generate_reply(self, interviewer_text: str) -> str:
        reply = self.llm.reply(self.system_prompt, self._history, interviewer_text)
        self._history.append({"role": "user", "content": interviewer_text})
        self._history.append({"role": "assistant", "content": reply})
        return reply

    def finish(self, ended_by: str):
        return self.recorder.finish(ended_by=ended_by)  # type: ignore[arg-type]
