"""OpenAI chat completions returning JSON objects."""

from __future__ import annotations

import json

from openai import OpenAI

from interviewees.env import require_env

MAX_JSON_ATTEMPTS = 3

# Reasoning models (gpt-5, o-series) only accept the default temperature.
_NO_CUSTOM_TEMPERATURE_PREFIXES = ("gpt-5", "o1", "o3", "o4")


def model_supports_custom_temperature(model: str) -> bool:
    m = model.lower().strip()
    return not any(m.startswith(prefix) for prefix in _NO_CUSTOM_TEMPERATURE_PREFIXES)


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
    kwargs: dict = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if model_supports_custom_temperature(model):
        kwargs["temperature"] = temperature
    res = client.chat.completions.create(**kwargs)
    content = (res.choices[0].message.content or "").strip()
    return json.loads(content), content
