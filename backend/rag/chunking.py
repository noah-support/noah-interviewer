from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    chunk_id: int
    text: str


def chunk_text(
    text: str,
    *,
    max_chars: int = 1200,
    overlap: int = 200,
) -> list[Chunk]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    cleaned = "\n".join(line.strip() for line in cleaned.splitlines())
    cleaned = "\n".join([line for line in cleaned.split("\n") if line != ""])

    chunks: list[Chunk] = []
    start = 0
    cid = 0
    n = len(cleaned)

    max_chars = max(200, int(max_chars))
    overlap = max(0, min(int(overlap), max_chars - 50))

    while start < n:
        end = min(n, start + max_chars)
        window = cleaned[start:end]
        last_break = window.rfind("\n")
        if last_break > 200:
            end = start + last_break

        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(Chunk(chunk_id=cid, text=chunk))
            cid += 1

        if end >= n:
            break
        start = max(0, end - overlap)

    return chunks

