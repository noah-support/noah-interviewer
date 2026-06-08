from interviewees.core.llm_json import model_supports_custom_temperature


def test_gpt5_omits_custom_temperature() -> None:
    assert not model_supports_custom_temperature("gpt-5")
    assert not model_supports_custom_temperature("GPT-5-mini")


def test_gpt4o_supports_custom_temperature() -> None:
    assert model_supports_custom_temperature("gpt-4o")
    assert model_supports_custom_temperature("gpt-4o-mini")
