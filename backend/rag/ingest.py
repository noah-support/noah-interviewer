from __future__ import annotations

from dataclasses import dataclass

from rag.chunking import Chunk, chunk_text
from rag.embeddings import embed_texts
from rag.extract import extract_text
import os

from pinecone import Pinecone  # type: ignore[import-not-found]


@dataclass(frozen=True)
class IngestResult:
    chunk_count: int


def ingest_document(
    *,
    namespace: str,
    doc_id: int,
    filename: str,
    content_type: str | None,
    data: bytes,
) -> IngestResult:
    text = extract_text(filename=filename, content_type=content_type, data=data)
    chunks: list[Chunk] = chunk_text(text)
    if not chunks:
        return IngestResult(chunk_count=0)

    embeddings = embed_texts([c.text for c in chunks])
    vectors = []
    for c, emb in zip(chunks, embeddings, strict=True):
        vectors.append(
            {
                "id": f"doc-{doc_id}-chunk-{c.chunk_id}",
                "values": emb,
                "metadata": {
                    "doc_id": doc_id,
                    "chunk_id": c.chunk_id,
                    "source_filename": filename,
                    "text": c.text,
                },
            }
        )

    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME", "interviewer-docs")
    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)
    index.upsert(namespace=namespace, vectors=vectors)
    return IngestResult(chunk_count=len(chunks))

