from interviewees.core.llm_json import model_supports_custom_temperature, parse_json_content


def test_gpt5_omits_custom_temperature() -> None:
    assert not model_supports_custom_temperature("gpt-5")
    assert not model_supports_custom_temperature("GPT-5-mini")


def test_gpt4o_supports_custom_temperature() -> None:
    assert model_supports_custom_temperature("gpt-4o")
    assert model_supports_custom_temperature("gpt-4o-mini")


def test_parse_json_content_strips_markdown_fence() -> None:
    raw = '```json\n{"scores": {"a": 1}}\n```'
    assert parse_json_content(raw) == {"scores": {"a": 1}}
