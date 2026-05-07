from __future__ import annotations

from io import BytesIO
from typing import Optional


def _normalize_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()


def extract_text(*, filename: str, content_type: Optional[str], data: bytes) -> str:
    """
    Extract plain text from supported uploads.

    Supported:
    - .pdf (pypdf)
    - .docx (python-docx)
    - .txt / .md (utf-8)
    """
    name = (filename or "").lower()
    ctype = (content_type or "").lower()

    if name.endswith(".pdf") or ctype == "application/pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        parts: list[str] = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        return _normalize_text("\n\n".join(parts))

    if name.endswith(".docx") or ctype in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        import docx  # type: ignore[import-not-found]

        doc = docx.Document(BytesIO(data))
        parts = [p.text for p in doc.paragraphs if p.text]
        return _normalize_text("\n".join(parts))

    if name.endswith(".txt") or name.endswith(".md") or ctype.startswith("text/") or not ctype:
        try:
            return _normalize_text(data.decode("utf-8"))
        except UnicodeDecodeError:
            return _normalize_text(data.decode("utf-8", errors="replace"))

    raise ValueError(f"Unsupported file type: filename={filename!r} content_type={content_type!r}")

