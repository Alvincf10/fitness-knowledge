"""Hallucination / low-confidence guard."""

from __future__ import annotations

from .config import RetrievalConfig
from .models import RetrievalHit, RetrievalResult


INSUFFICIENT_EVIDENCE = "Insufficient evidence found in the current knowledge base."


def apply_guard(
    query: str,
    hits: list[RetrievalHit],
    cfg: RetrievalConfig,
    *,
    expanded_query: str | None = None,
) -> RetrievalResult:
    """Block answers when top score is below the configured threshold."""
    threshold = cfg.confidence_threshold
    message = cfg.insufficient_evidence_message or INSUFFICIENT_EVIDENCE
    top_score = hits[0].score if hits else 0.0

    if not hits or top_score < threshold:
        return RetrievalResult(
            query=query,
            hits=[],
            insufficient_evidence=True,
            message=message,
            expanded_query=expanded_query,
        )

    return RetrievalResult(
        query=query,
        hits=hits,
        insufficient_evidence=False,
        message=None,
        expanded_query=expanded_query,
    )
