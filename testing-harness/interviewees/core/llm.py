"""OpenAI chat completions wrapper for interviewee replies."""

from __future__ import annotations

from typing import Literal

from openai import OpenAI

from interviewees.env import require_env

ChatRole = Literal["user", "assistant"]


class IntervieweeLLM:
    """Generate interviewee responses via OpenAI Chat Completions."""

    def __init__(self, model: str | None = None) -> None:
        self._client = OpenAI(api_key=require_env("OPENAI_API_KEY"))
        self._model = model or "gpt-4o"

    def reply(
        self,
        system: str,
        history: list[dict[str, str]],
        user_text: str,
    ) -> str:
        """
        Generate the next interviewee turn.

        history uses OpenAI roles: interviewer messages are ``user``,
        prior interviewee messages are ``assistant``.
        """
        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_text})

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.2,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI returned empty content")
        return content.strip()
