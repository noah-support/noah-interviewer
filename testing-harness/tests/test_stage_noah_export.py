import json
from pathlib import Path

from interviewees.evaluation.stage import stage_noah_export


def test_stage_noah_export_writes_canonical_files(tmp_path: Path) -> None:
    root = tmp_path / "personas"
    (root / "A").mkdir(parents=True)
    export = {
        "A": {
            "content": {"turns": [{"role": "interviewer", "text": "Hi"}]},
            "summary": "Done",
            "discovery_state_json": {"meta": {"phase": "roundup"}},
        }
    }
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(export), encoding="utf-8")

    written = stage_noah_export(export_path, root)
    names = {p.name for p in written}
    assert "noah_transcript.json" in names
    assert "noah_summary.txt" in names
    assert "noah_state.json" in names
    assert (root / "A" / "noah_transcript.json").is_file()
