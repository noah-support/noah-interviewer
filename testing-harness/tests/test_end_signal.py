from interviewees.core.end_signal import (
    SENTINEL,
    contains_sentinel,
    ended_by_for_disconnect,
    is_interviewer_closing_message,
    strip_sentinel,
)


def test_contains_sentinel_present():
    assert contains_sentinel(f"Thanks! {SENTINEL}")
    assert contains_sentinel(SENTINEL)


def test_contains_sentinel_absent():
    assert not contains_sentinel("Thanks, goodbye!")
    assert not contains_sentinel("[[interview_complete]]")


def test_strip_sentinel():
    assert strip_sentinel(f"Thanks.\n{SENTINEL}") == "Thanks."
    assert strip_sentinel(f"{SENTINEL} Done.") == "Done."
    assert strip_sentinel("No sentinel here") == "No sentinel here"


def test_sentinel_case_sensitive():
    assert not contains_sentinel("[[INTERVIEW_complete]]")


_NOAH_STYLE_CLOSE = (
    "Thanks for that. I think we've covered all the important ground here — your role, "
    "your daily tasks and time breakdown, your strengths in process optimization, the main "
    "bottlenecks like chasing student information and manual status updates, and your clear "
    "ambitions to focus more on improvement work.\n\n"
    "You've been really helpful, Emily. You can now press the red button to end the "
    "conversation whenever you're ready."
)


def test_is_interviewer_closing_noah_red_button():
    assert is_interviewer_closing_message(_NOAH_STYLE_CLOSE)
    assert ended_by_for_disconnect(_NOAH_STYLE_CLOSE) == "closing"


def test_is_interviewer_closing_sentinel_takes_precedence():
    text = f"{_NOAH_STYLE_CLOSE}\n{SENTINEL}"
    assert ended_by_for_disconnect(text) == "sentinel"


def test_is_interviewer_closing_not_mid_interview():
    assert not is_interviewer_closing_message(
        "Thanks. Could you walk me through the first step in Sipac?"
    )
