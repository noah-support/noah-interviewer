import json
from pathlib import Path

import pytest

from interviewees.persona_layout import persona_json_in_folder
from interviewees.project_runner import discover_persona_folders

_MINIMAL_PERSONA = {
    "name": "Test User",
    "role": "Tester",
    "backstory": "A test persona for discovery.",
    "processes": [
        {
            "process_name": "Test process",
            "steps": [
                {
                    "step_name": "Do thing",
                    "software_tools_used": [],
                    "time_needed": "5 minutes",
                    "handoff_to": None,
                }
            ],
            "exceptions": [
                {
                    "what_goes_wrong": "Failure",
                    "impact": "Delay",
                    "recovery": "Retry",
                }
            ],
        }
    ],
}


def _write_persona_json(folder: Path) -> None:
    persona_json_in_folder(folder).write_text(
        json.dumps(_MINIMAL_PERSONA, indent=2),
        encoding="utf-8",
    )


def test_discover_persona_folders(tmp_path: Path) -> None:
    folder_a = tmp_path / "A"
    folder_b = tmp_path / "B"
    folder_a.mkdir()
    folder_b.mkdir()
    _write_persona_json(folder_a)
    _write_persona_json(folder_b)
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")

    specs = discover_persona_folders(tmp_path)
    assert [s.folder_name for s in specs] == ["A", "B"]
    assert specs[0].json_path == persona_json_in_folder(folder_a)


def test_discover_missing_persona_json(tmp_path: Path) -> None:
    (tmp_path / "A").mkdir()
    with pytest.raises(Exception):
        discover_persona_folders(tmp_path)


def test_discover_empty_root(tmp_path: Path) -> None:
    with pytest.raises(Exception):
        discover_persona_folders(tmp_path)
