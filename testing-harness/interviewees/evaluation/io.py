"""JSON read/write for evaluation artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(
    path: Path,
    payload: BaseModel | dict[str, Any],
    *,
    force: bool = False,
) -> None:
    if path.exists() and not force:
        raise RuntimeError(f"Refusing to overwrite existing file: {path}")

    if isinstance(payload, BaseModel):
        data = payload.model_dump(mode="json")
    else:
        data = payload

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str, *, force: bool = False) -> None:
    if path.exists() and not force:
        raise RuntimeError(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
