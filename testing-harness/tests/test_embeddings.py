from interviewees.core.embeddings import _sanitize_embedding_input, embed_texts


def test_sanitize_embedding_input_replaces_blank() -> None:
    assert _sanitize_embedding_input("") == "[empty]"
    assert _sanitize_embedding_input("   ") == "[empty]"
    assert _sanitize_embedding_input("hello") == "hello"


def test_embed_texts_replaces_empty_strings(monkeypatch) -> None:
    captured: list[list[str]] = []

    class FakeData:
        def __init__(self, index: int, embedding: list[float]) -> None:
            self.index = index
            self.embedding = embedding

    class FakeResp:
        data = [FakeData(0, [1.0]), FakeData(1, [0.0]), FakeData(2, [0.5])]

    class FakeEmbeddings:
        def create(self, **kwargs):
            captured.append(kwargs["input"])
            return FakeResp()

    class FakeClient:
        embeddings = FakeEmbeddings()

    monkeypatch.setattr(
        "interviewees.core.embeddings.OpenAI",
        lambda api_key: FakeClient(),
    )
    monkeypatch.setattr("interviewees.core.embeddings.require_env", lambda k: "test-key")

    embed_texts(["alpha", "", "  "])
    assert captured == [["alpha", "[empty]", "[empty]"]]
