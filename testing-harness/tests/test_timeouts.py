from interviewees.core.timeouts import interviewee_reply_delay_s, interviewer_idle_timeout_s


def test_interviewer_idle_timeout_default(monkeypatch):
    monkeypatch.delenv("INTERVIEWER_IDLE_TIMEOUT_S", raising=False)
    assert interviewer_idle_timeout_s() == 600.0


def test_interviewee_reply_delay_default(monkeypatch):
    monkeypatch.delenv("INTERVIEWEE_REPLY_DELAY_S", raising=False)
    assert interviewee_reply_delay_s() == 2.5


def test_interviewee_reply_delay_zero(monkeypatch):
    monkeypatch.setenv("INTERVIEWEE_REPLY_DELAY_S", "0")
    assert interviewee_reply_delay_s() == 0.0
