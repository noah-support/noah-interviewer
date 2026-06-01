import os
from pathlib import Path

import interviewees.env as env_mod
from interviewees.env import load_harness_env, require_env


def test_load_harness_env_from_file(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=test-key-from-dotenv\n", encoding="utf-8")
    monkeypatch.setattr(env_mod, "_loaded", False)
    monkeypatch.setattr(env_mod, "harness_root", lambda: tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    load_harness_env()
    assert os.environ.get("OPENAI_API_KEY") == "test-key-from-dotenv"
    assert require_env("OPENAI_API_KEY") == "test-key-from-dotenv"
