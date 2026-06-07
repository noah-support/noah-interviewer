from interviewees.evaluation.report_markdown import render_validation_markdown


def test_render_validation_markdown_sections() -> None:
    reports = {
        "noah": {
            "reconstruction_file": "result_noah.json",
            "embeddings": {
                "overall_similarity": 0.85,
                "counts": {
                    "missed_processes": 0,
                    "extra_processes": 1,
                    "missed_steps": 0,
                    "extra_steps": 0,
                    "missed_exceptions": 0,
                    "extra_exceptions": 0,
                },
                "process_reports": [],
                "missed_processes": [],
                "extra_processes": [],
            },
            "judge": {
                "scores": {"activity_coverage": 4},
                "justifications": {"activity_coverage": "Most steps captured."},
            },
        }
    }
    md = render_validation_markdown("A", reports)
    assert "# Validation report — persona A" in md
    assert "## Noah" in md
    assert "activity_coverage" in md.lower() or "Activity Coverage" in md
    assert "backstory ignored" in md
