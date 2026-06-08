from interviewees.evaluation.pipeline import SummaryRow
from interviewees.evaluation.report import format_run_report


def test_format_run_report_lists_errors_and_skips() -> None:
    rows = [
        SummaryRow(folder="A", system="noah", run_id="run_1", status="ok"),
        SummaryRow(
            folder="B",
            system="elevenlabs",
            run_id="run_1",
            status="error",
            error="judge failed",
        ),
        SummaryRow(
            folder="C",
            system="noah",
            run_id="run_1",
            status="skipped",
            error="no interview artifacts found",
        ),
    ]
    text = format_run_report(rows)
    assert "1/3 ok, 1 skipped, 1 errors" in text
    assert "[run_1/B/elevenlabs] judge failed" in text
    assert "[run_1/C/noah] no interview artifacts found" in text
