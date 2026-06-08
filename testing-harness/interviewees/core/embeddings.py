"""OpenAI embeddings for evaluation field comparison."""

from __future__ import annotations

import os
from typing import Iterable

from openai import OpenAI

from interviewees.env import load_harness_env, require_env

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"
DEFAULT_EMBEDDING_DIMENSIONS = 1024

# OpenAI rejects empty strings in embedding input batches.
_EMPTY_EMBEDDING_INPUT = "[empty]"


def embedding_model() -> str:
    load_harness_env()
    return (os.environ.get("OPENAI_EMBEDDING_MODEL") or DEFAULT_EMBEDDING_MODEL).strip()


def embedding_dimensions() -> int:
    load_harness_env()
    raw = (os.environ.get("OPENAI_EMBEDDING_DIMENSIONS") or "").strip()
    if raw:
        return int(raw)
    return DEFAULT_EMBEDDING_DIMENSIONS


def _sanitize_embedding_input(text: str) -> str:
    t = text if isinstance(text, str) else str(text)
    return t.strip() or _EMPTY_EMBEDDING_INPUT


def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    """Embed strings; empty input returns []. Blank strings are replaced before the API call."""
    items = [_sanitize_embedding_input(t) for t in texts]
    if not items:
        return []

    client = OpenAI(api_key=require_env("OPENAI_API_KEY"))
    resp = client.embeddings.create(
        model=embedding_model(),
        input=items,
        dimensions=embedding_dimensions(),
    )
    data = sorted(resp.data, key=lambda d: d.index)
    return [d.embedding for d in data]
