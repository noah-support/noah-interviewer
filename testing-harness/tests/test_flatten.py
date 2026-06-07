from interviewees.evaluation.flatten import flatten_profile
from interviewees.evaluation.reconstructed_schema import (
    GroundTruthProfile,
    ReconstructedProcess,
)
from interviewees.core.persona_schema import Exception, Step


def test_flatten_includes_scalar_and_step_paths() -> None:
    profile = GroundTruthProfile(
        name="N",
        role="R",
        processes=[
            ReconstructedProcess(
                process_name="P",
                steps=[
                    Step(
                        step_name="S1",
                        software_tools_used=["Tool"],
                        time_needed="5m",
                        handoff_to=None,
                    )
                ],
                exceptions=[
                    Exception(
                        what_goes_wrong="x",
                        impact="y",
                        recovery="z",
                    )
                ],
            )
        ],
    )
    fields = flatten_profile(profile)
    paths = {f.path for f in fields}
    assert "name" in paths
    assert "processes[0].steps[0].step_name" in paths
    assert "processes[0].exceptions[0].recovery" in paths
