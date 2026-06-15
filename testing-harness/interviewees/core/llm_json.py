"""LLM chat completions returning JSON objects (OpenAI and Anthropic)."""

from __future__ import annotations

import json
import re

from anthropic import Anthropic
from openai import OpenAI

from interviewees.env import require_env

MAX_JSON_ATTEMPTS = 3

# Reasoning models (gpt-5, o-series) only accept the default temperature.
_NO_CUSTOM_TEMPERATURE_PREFIXES = ("gpt-5", "o1", "o3", "o4")

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def model_supports_custom_temperature(model: str) -> bool:
    m = model.lower().strip()
    return not any(m.startswith(prefix) for prefix in _NO_CUSTOM_TEMPERATURE_PREFIXES)


def parse_json_content(content: str) -> dict:
    """Parse a JSON object from raw model text, tolerating optional markdown fences."""
    text = content.strip()
    match = _JSON_FENCE_RE.match(text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def chat_json(
    *,
    system: str,
    user: str,
    model: str,
    temperature: float = 0.2,
) -> tuple[dict, str]:
    """
    Call the OpenAI chat API with json_object response format.

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
    return parse_json_content(content), content


def claude_json(
    *,
    system: str,
    user: str,
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> tuple[dict, str]:
    """
    Call the Anthropic Messages API and parse a JSON object from the response.

    Returns (parsed_dict, raw_content_string).
    """
    client = Anthropic(api_key=require_env("ANTHROPIC_API_KEY"))
    res = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text_blocks = [block.text for block in res.content if block.type == "text"]
    content = "\n".join(text_blocks).strip()
    if not content:
        raise RuntimeError("Anthropic returned empty content")
    return parse_json_content(content), content
