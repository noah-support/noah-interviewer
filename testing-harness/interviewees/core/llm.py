"""OpenAI chat completions wrapper for interviewee replies."""

from __future__ import annotations

import os
from typing import Literal

from openai import OpenAI

ChatRole = Literal["user", "assistant"]


class IntervieweeLLM:
    """Generate interviewee responses via OpenAI Chat Completions."""

    def __init__(self, model: str | None = None) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self._client = OpenAI(api_key=api_key)
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
            temperature=0.7,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI returned empty content")
        return content.strip()
