from pathlib import Path
from unittest.mock import MagicMock, patch

from interviewees.core.persona import load_persona
from interviewees.core.session import SMOKE_TURN_CAP, turn_cap_for_mode, InterviewSession

_FIXTURE = Path(__file__).parent / "fixtures" / "sample_persona.json"


def test_turn_cap_for_mode():
    assert turn_cap_for_mode("smoke") == SMOKE_TURN_CAP
    assert turn_cap_for_mode("full") is None


@patch.object(InterviewSession, "_generate_reply", return_value="ok")
def test_smoke_mode_ends_at_turn_cap(mock_reply: MagicMock):
    persona = load_persona(_FIXTURE, subject_label="T")
    session = InterviewSession(
        persona,
        interviewer="elevenlabs",
        mode="smoke",
        openai_model="gpt-4o",
    )
    for i in range(SMOKE_TURN_CAP):
        reply, disconnect = session.handle_interviewer_message(f"Q{i}?")
        assert reply == "ok"
        assert disconnect is False

    reply, disconnect = session.handle_interviewer_message("One more?")
    assert disconnect is True
    assert reply is not None
    assert mock_reply.call_count == SMOKE_TURN_CAP
