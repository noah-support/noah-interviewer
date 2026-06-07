"""OpenAI embeddings for evaluation field comparison."""

from __future__ import annotations

import os
from typing import Iterable

from openai import OpenAI

from interviewees.env import load_harness_env, require_env

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"
DEFAULT_EMBEDDING_DIMENSIONS = 1024


def embedding_model() -> str:
    load_harness_env()
    return (os.environ.get("OPENAI_EMBEDDING_MODEL") or DEFAULT_EMBEDDING_MODEL).strip()


def embedding_dimensions() -> int:
    load_harness_env()
    raw = (os.environ.get("OPENAI_EMBEDDING_DIMENSIONS") or "").strip()
    if raw:
        return int(raw)
    return DEFAULT_EMBEDDING_DIMENSIONS


def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    """Embed strings; empty input returns []."""
    items = [t if isinstance(t, str) else str(t) for t in texts]
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
