"""Hybrid fusion: Reciprocal Rank Fusion and weighted score fusion."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Sequence

from .models import RetrievalHit

_STOP = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "do",
    "does",
    "did",
    "how",
    "what",
    "why",
    "when",
    "where",
    "which",
    "who",
    "i",
    "me",
    "my",
    "for",
    "to",
    "of",
    "in",
    "on",
    "and",
    "or",
    "with",
    "this",
    "that",
    "it",
    "be",
    "should",
    "can",
    "will",
    "much",
    "many",
    "need",
    "good",
    "best",
    "correctly",
    "answer",
    "fitness",
    "question",
    "about",
    "know",
}


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP and len(t) > 1}


def apply_title_boost(
    query: str,
    hits: list[RetrievalHit],
    *,
    boost: float = 0.05,
) -> list[RetrievalHit]:
    """Boost candidates whose title/slug strongly overlaps the query.

    Improves MRR for title-grounded questions without changing fusion math.
    """
    q = query.lower()
    q_tokens = _tokens(query)
    if not hits:
        return hits

    boosted: list[RetrievalHit] = []
    for hit in hits:
        chunk = hit.chunk
        title = (chunk.title if chunk else "") or ""
        slug = ((chunk.slug if chunk else "") or "").replace("-", " ")
        path = hit.citation.file_path
        stem = path.rsplit("/", 1)[-1].removesuffix(".md").replace("-", " ")
        title_l = title.lower()
        score = hit.score
        extra = 0.0
        if title_l and title_l in q:
            extra = 1.0
        elif stem and stem in q:
            extra = 0.9
        else:
            t_tokens = _tokens(title) | _tokens(slug) | _tokens(stem)
            if t_tokens:
                extra = len(q_tokens & t_tokens) / len(t_tokens)
        new_score = score + boost * extra
        boosted.append(
            RetrievalHit(
                chunk_id=hit.chunk_id,
                score=new_score,
                citation=hit.citation,
                chunk=hit.chunk,
            )
        )
    boosted.sort(key=lambda h: h.score, reverse=True)
    return boosted


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[tuple[str, float]]],
    *,
    k: int = 60,
    top_n: int = 30,
) -> list[tuple[str, float]]:
    """Combine ranked lists with RRF. Scores in input lists are ignored for ranking."""
    scores: dict[str, float] = defaultdict(float)
    for ranked in ranked_lists:
        for rank, (doc_id, _score) in enumerate(ranked, start=1):
            scores[doc_id] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]


def weighted_score_fusion(
    semantic: Sequence[tuple[str, float]],
    bm25: Sequence[tuple[str, float]],
    *,
    semantic_weight: float = 0.6,
    bm25_weight: float = 0.4,
    top_n: int = 30,
) -> list[tuple[str, float]]:
    """Min-max normalize each list then weight-sum."""

    def normalize(items: Sequence[tuple[str, float]]) -> dict[str, float]:
        if not items:
            return {}
        vals = [s for _, s in items]
        lo, hi = min(vals), max(vals)
        if hi - lo < 1e-12:
            return {i: 1.0 for i, _ in items}
        return {i: (s - lo) / (hi - lo) for i, s in items}

    sem = normalize(semantic)
    lex = normalize(bm25)
    ids = set(sem) | set(lex)
    fused = {
        i: semantic_weight * sem.get(i, 0.0) + bm25_weight * lex.get(i, 0.0) for i in ids
    }
    return sorted(fused.items(), key=lambda x: x[1], reverse=True)[:top_n]


def fuse(
    semantic: Sequence[tuple[str, float]],
    bm25: Sequence[tuple[str, float]],
    *,
    method: str = "rrf",
    rrf_k: int = 60,
    semantic_weight: float = 0.6,
    bm25_weight: float = 0.4,
    top_n: int = 30,
) -> list[tuple[str, float]]:
    method_l = method.lower()
    if method_l == "rrf":
        return reciprocal_rank_fusion([semantic, bm25], k=rrf_k, top_n=top_n)
    if method_l == "weighted":
        return weighted_score_fusion(
            semantic,
            bm25,
            semantic_weight=semantic_weight,
            bm25_weight=bm25_weight,
            top_n=top_n,
        )
    raise ValueError(f"Unknown fusion method: {method}")
