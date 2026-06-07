"""OpenAI chat completions returning JSON objects."""

from __future__ import annotations

import json

from openai import OpenAI

from interviewees.env import require_env

MAX_JSON_ATTEMPTS = 3


def chat_json(
    *,
    system: str,
    user: str,
    model: str,
    temperature: float = 0.2,
) -> tuple[dict, str]:
    """
    Call the chat API with json_object response format.

    Returns (parsed_dict, raw_content_string).
    """
    client = OpenAI(api_key=require_env("OPENAI_API_KEY"))
    res = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    content = (res.choices[0].message.content or "").strip()
    return json.loads(content), content
