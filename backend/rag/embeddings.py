from __future__ import annotations

import os
from typing import Iterable, List

from openai import OpenAI


def _openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY (required for embeddings)")
    return OpenAI(api_key=api_key)


def embed_texts(
    texts: Iterable[str],
    *,
    model: str = "text-embedding-3-large",
    dimensions: int = 1024,
) -> List[List[float]]:
    items = [t if isinstance(t, str) else str(t) for t in texts]
    if not items:
        return []

    client = _openai_client()
    resp = client.embeddings.create(model=model, input=items, dimensions=dimensions)
    data = sorted(resp.data, key=lambda d: d.index)
    return [d.embedding for d in data]

