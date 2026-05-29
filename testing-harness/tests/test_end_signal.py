from interviewees.core.end_signal import SENTINEL, contains_sentinel, strip_sentinel


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
