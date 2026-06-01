import json
from pathlib import Path

from tools.prepare_personas import _load_merged_fragments_from_folder, _resolve_fragment_source


def test_resolve_fragment_source_from_datasets(tmp_path: Path) -> None:
    datasets = tmp_path / "datasets"
    dataset_dir = datasets / "caseHandling_1"
    dataset_dir.mkdir(parents=True)
    fragments = {
        "fragments": [
            {
                "id": "start",
                "name": "Start",
                "type": "START_EVENT",
                "branch": "0",
                "inComing": [],
                "outComing": ["t1"],
            },
            {
                "id": "t1",
                "name": "Do work",
                "type": "TASK",
                "branch": "0",
                "inComing": ["start"],
                "outComing": ["end"],
            },
            {
                "id": "end",
                "name": "End",
                "type": "END_EVENT",
                "branch": "0",
                "inComing": ["t1"],
                "outComing": [],
            },
        ]
    }
    (dataset_dir / "S0_caseHandling_1.json").write_text(
        json.dumps(fragments),
        encoding="utf-8",
    )

    persona_dir = tmp_path / "personas" / "A"
    persona_dir.mkdir(parents=True)
    stub = persona_dir / "process1.json"
    stub.write_text('{"Atividades": []}', encoding="utf-8")

    source = _resolve_fragment_source(stub, datasets_root=datasets)
    assert source.name == "S0_caseHandling_1.json"

    merged, sources = _load_merged_fragments_from_folder(persona_dir, datasets_root=datasets)
    assert len(merged) == 3
    assert merged[0].id == "process1__start"
    assert "process1.json" in sources[0]
