from interviewees.evaluation.reconstructed_schema import ReconstructedPersona


def test_empty_persona_valid() -> None:
    p = ReconstructedPersona.model_validate({"name": "", "role": "", "processes": []})
    assert p.processes == []


def test_sparse_process() -> None:
    p = ReconstructedPersona.model_validate(
        {
            "name": "Alex",
            "role": "",
            "processes": [
                {
                    "process_name": "P1",
                    "steps": [],
                    "exceptions": [],
                }
            ],
        }
    )
    assert p.name == "Alex"
