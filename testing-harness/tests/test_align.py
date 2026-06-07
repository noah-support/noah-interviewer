from unittest.mock import patch

from interviewees.evaluation.align import cosine_similarity, greedy_align


def test_cosine_identical() -> None:
    v = [1.0, 0.0, 0.0]
    assert cosine_similarity(v, v) == 1.0


def test_greedy_align_with_mock_embeddings() -> None:
    truth = [(0, "alpha"), (1, "beta")]
    recon = [(0, "alpha copy"), (1, "gamma")]

    def fake_embed(texts):
        out = []
        for t in texts:
            if "alpha" in t:
                out.append([1.0, 0.0])
            elif "beta" in t:
                out.append([0.0, 1.0])
            else:
                out.append([0.5, 0.5])
        return out

    with patch("interviewees.evaluation.align.embed_texts", side_effect=fake_embed):
        result = greedy_align(truth, recon, min_similarity=0.0)

    assert len(result.pairs) == 2
    assert result.pairs[0].truth_index == 0
    assert result.pairs[0].recon_index == 0
