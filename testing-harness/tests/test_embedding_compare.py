from unittest.mock import patch

from interviewees.evaluation.embedding_compare import compare_embeddings
from interviewees.evaluation.reconstructed_schema import (
    GroundTruthProfile,
    ReconstructedPersona,
    ReconstructedProcess,
)
from interviewees.core.persona_schema import Exception, Step


def _profile() -> GroundTruthProfile:
    proc = ReconstructedProcess(
        process_name="Repair",
        steps=[
            Step(
                step_name="Fix item",
                software_tools_used=["ERP"],
                time_needed="1 hour",
                handoff_to="QA",
            )
        ],
        exceptions=[
            Exception(what_goes_wrong="delay", impact="late", recovery="notify")
        ],
    )
    return GroundTruthProfile(name="Sam", role="Tech", processes=[proc])


def test_compare_embeddings_mocked() -> None:
    truth = _profile()
    recon = ReconstructedPersona(
        name="Sam",
        role="Technician",
        processes=truth.processes,
    )

    def fake_embed(texts):
        return [[1.0, 0.0] for _ in texts]

    with patch("interviewees.evaluation.embedding_compare.embed_texts", side_effect=fake_embed):
        with patch("interviewees.evaluation.align.embed_texts", side_effect=fake_embed):
            report = compare_embeddings(truth, recon)

    assert report.overall_similarity >= 0.99
    assert report.counts["missed_processes"] == 0
