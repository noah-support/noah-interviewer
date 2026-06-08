import json
from pathlib import Path

from interviewees.evaluation.run_folder import discover_noah_export, resolve_run_paths
from interviewees.evaluation.stage import stage_elevenlabs_exports, stage_from_run_folder


def test_discover_noah_export_picks_latest(tmp_path: Path) -> None:
    noah = tmp_path / "noah"
    noah.mkdir()
    (noah / "output-test-noah_20260101T000000Z.json").write_text("{}", encoding="utf-8")
    latest = noah / "output-test-noah_20260201T000000Z.json"
    latest.write_text("{}", encoding="utf-8")
    assert discover_noah_export(tmp_path) == latest


def test_resolve_run_paths_maps_validation_output(tmp_path: Path) -> None:
    harness = tmp_path / "harness"
    run_dir = harness / "results" / "run_1"
    (run_dir / "noah").mkdir(parents=True)
    (run_dir / "elevenlabs").mkdir(parents=True)
    (run_dir / "noah" / "output-test-noah_20260101T000000Z.json").write_text("{}", encoding="utf-8")

    paths = resolve_run_paths(run_dir, harness_root=harness)
    assert paths.run_id == "run_1"
    assert paths.validation_root == harness / "results" / "validation" / "run_1"
    assert paths.noah_export is not None


def test_stage_elevenlabs_exports_copies_per_folder(tmp_path: Path) -> None:
    root = tmp_path / "validation"
    (root / "A").mkdir(parents=True)
    exports = tmp_path / "elevenlabs"
    exports.mkdir()
    exports.joinpath("A.json").write_text('[{"role":"user","message":"hi"}]', encoding="utf-8")

    written = stage_elevenlabs_exports(exports, root)
    assert len(written) == 1
    assert (root / "A" / "elevenlabs_transcript.json").is_file()


def test_stage_from_run_folder_end_to_end(tmp_path: Path) -> None:
    harness = tmp_path / "harness"
    gt = harness / "personas"
    (gt / "A").mkdir(parents=True)
    (gt / "A" / "persona.json").write_text(
        json.dumps({"name": "A", "role": "r", "processes": []}),
        encoding="utf-8",
    )

    run_dir = harness / "results" / "run_2"
    (run_dir / "noah").mkdir(parents=True)
    (run_dir / "elevenlabs").mkdir(parents=True)
    export = {
        "A": {
            "content": {"items": [{"role": "user", "content": "hello"}]},
            "summary": "summary text",
            "discovery_state_json": {"meta": {"phase": "roundup"}},
        }
    }
    (run_dir / "noah" / "output-test-noah_20260101T000000Z.json").write_text(
        json.dumps(export),
        encoding="utf-8",
    )
    (run_dir / "elevenlabs" / "A.json").write_text(
        '[{"role":"user","message":"hi"}]',
        encoding="utf-8",
    )

    paths = resolve_run_paths(run_dir, harness_root=harness, ground_truth_root=gt)
    staged = stage_from_run_folder(paths, force=True)
    names = {p.name for p in staged}
    assert "persona.json" in names
    assert "noah_transcript.json" in names
    assert "elevenlabs_transcript.json" in names
    assert "run_manifest.json" in names
    assert (paths.validation_root / "run_manifest.json").is_file()

    # Re-staging without --force should be idempotent (retry after failed evaluation).
    stage_from_run_folder(paths, force=False)
