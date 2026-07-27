"""Dynamic Top-K selection based on retrieval confidence."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DynamicTopKBands:
    """Confidence bands → final context count."""

    high_threshold: float = 0.7
    medium_threshold: float = 0.4
    high_k: int = 3
    medium_k: int = 5
    low_k: int = 10


def select_dynamic_topk(
    confidence: float,
    *,
    bands: DynamicTopKBands | None = None,
    min_k: int = 3,
    max_k: int = 10,
    enabled: bool = True,
    default_k: int = 5,
) -> int:
    """Return Top-K for context packing from a confidence estimate."""
    if not enabled:
        return max(min_k, min(max_k, default_k))
    b = bands or DynamicTopKBands()
    if confidence >= b.high_threshold:
        k = b.high_k
    elif confidence >= b.medium_threshold:
        k = b.medium_k
    else:
        k = b.low_k
    return max(min_k, min(max_k, k))
