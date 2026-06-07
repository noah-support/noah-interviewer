from pathlib import Path

import pytest

from interviewees.evaluation.interview_artifacts import (
    discover_interview_artifacts,
    is_denied_input,
)


def test_denylist_blocks_ground_truth() -> None:
    assert is_denied_input(Path("persona.json"))
    assert is_denied_input(Path("process1.json"))
    assert is_denied_input(Path("result_noah.json"))
    assert is_denied_input(Path("validation_noah.json"))
    assert is_denied_input(Path("validation.md"))
    assert not is_denied_input(Path("noah_transcript.json"))


def test_discover_canonical_noah(tmp_path: Path) -> None:
    folder = tmp_path / "A"
    folder.mkdir()
    (folder / "noah_transcript.txt").write_text("Interviewer: Hi\nInterviewee: Hello", encoding="utf-8")
    (folder / "noah_summary.txt").write_text("Summary here", encoding="utf-8")
    (folder / "persona.json").write_text("{}", encoding="utf-8")

    art = discover_interview_artifacts(folder, "noah")
    assert art is not None
    assert "noah_transcript.txt" in art.source_files
    assert "Hi" in art.transcript_text


def test_discover_missing_returns_none(tmp_path: Path) -> None:
    folder = tmp_path / "A"
    folder.mkdir()
    assert discover_interview_artifacts(folder, "elevenlabs") is None


def test_persona_json_never_in_sources(tmp_path: Path) -> None:
    folder = tmp_path / "A"
    folder.mkdir()
    (folder / "persona.json").write_text('{"name":"x"}', encoding="utf-8")
    (folder / "elevenlabs_summary.txt").write_text("only summary", encoding="utf-8")
    art = discover_interview_artifacts(folder, "elevenlabs")
    assert art is not None
    assert "persona.json" not in art.source_files
