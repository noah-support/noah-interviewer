from pathlib import Path

import pytest

from interviewees.persona_layout import prompt_file_in_folder
from interviewees.project_runner import discover_persona_folders


def test_discover_persona_folders(tmp_path: Path) -> None:
    folder_a = tmp_path / "A"
    folder_b = tmp_path / "B"
    folder_a.mkdir()
    folder_b.mkdir()
    prompt_file_in_folder(folder_a).write_text("id: x\n", encoding="utf-8")
    prompt_file_in_folder(folder_b).write_text("id: y\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")

    specs = discover_persona_folders(tmp_path)
    assert [s.folder_name for s in specs] == ["A", "B"]
    assert specs[0].yaml_path == prompt_file_in_folder(folder_a)


def test_discover_legacy_sibling_yaml(tmp_path: Path) -> None:
    (tmp_path / "A").mkdir()
    (tmp_path / "A.yaml").write_text("id: legacy\n", encoding="utf-8")

    specs = discover_persona_folders(tmp_path)
    assert specs[0].yaml_path == tmp_path / "A.yaml"


def test_discover_missing_prompt(tmp_path: Path) -> None:
    (tmp_path / "A").mkdir()
    with pytest.raises(Exception):
        discover_persona_folders(tmp_path)


def test_discover_empty_root(tmp_path: Path) -> None:
    with pytest.raises(Exception):
        discover_persona_folders(tmp_path)
