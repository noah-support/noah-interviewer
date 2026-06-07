"""Greedy cosine-similarity alignment for list items."""

from __future__ import annotations

from dataclasses import dataclass

from interviewees.core.embeddings import embed_texts


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


@dataclass(frozen=True)
class AlignmentPair:
    truth_index: int
    recon_index: int
    similarity: float
    truth_text: str
    recon_text: str


@dataclass(frozen=True)
class AlignmentResult:
    pairs: list[AlignmentPair]
    missed_truth: list[tuple[int, str]]
    extra_recon: list[tuple[int, str]]


def greedy_align(
    truth_items: list[tuple[int, str]],
    recon_items: list[tuple[int, str]],
    *,
    min_similarity: float = 0.0,
) -> AlignmentResult:
    """
    Match items by highest cosine similarity on embeddings (greedy, one-to-one).
    """
    if not truth_items and not recon_items:
        return AlignmentResult(pairs=[], missed_truth=[], extra_recon=[])

    truth_texts = [t[1] for t in truth_items]
    recon_texts = [r[1] for r in recon_items]
    all_texts = truth_texts + recon_texts
    if not all_texts:
        return AlignmentResult(
            pairs=[],
            missed_truth=[(i, "") for i, _ in truth_items],
            extra_recon=[(i, "") for i, _ in recon_items],
        )

    embeddings = embed_texts(all_texts)
    t_embs = embeddings[: len(truth_texts)]
    r_embs = embeddings[len(truth_texts) :]

    used_t: set[int] = set()
    used_r: set[int] = set()
    pairs: list[AlignmentPair] = []

    while True:
        best_sim = -1.0
        best_t_idx = -1
        best_r_idx = -1
        for ti, _ in enumerate(truth_items):
            if ti in used_t:
                continue
            for ri, _ in enumerate(recon_items):
                if ri in used_r:
                    continue
                sim = cosine_similarity(t_embs[ti], r_embs[ri])
                if sim > best_sim:
                    best_sim = sim
                    best_t_idx = ti
                    best_r_idx = ri
        if best_t_idx < 0 or best_sim < min_similarity:
            break
        t_orig, t_text = truth_items[best_t_idx]
        r_orig, r_text = recon_items[best_r_idx]
        pairs.append(
            AlignmentPair(
                truth_index=t_orig,
                recon_index=r_orig,
                similarity=round(best_sim, 6),
                truth_text=t_text,
                recon_text=r_text,
            )
        )
        used_t.add(best_t_idx)
        used_r.add(best_r_idx)

    missed = [truth_items[i] for i in range(len(truth_items)) if i not in used_t]
    extra = [recon_items[i] for i in range(len(recon_items)) if i not in used_r]
    return AlignmentResult(pairs=pairs, missed_truth=missed, extra_recon=extra)
