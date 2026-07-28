"""Memory ranking by similarity, recency, and importance."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Sequence

from .models import MemoryConfig, MemoryRecord, RankedMemory

logger = logging.getLogger(__name__)


class MemoryRanker:
    """Score and rank memory candidates."""

    def __init__(self, config: MemoryConfig | None = None) -> None:
        from .config import load_memory_config

        self.config = config or load_memory_config()

    def rank(
        self,
        candidates: Sequence[tuple[MemoryRecord, float]],
        *,
        now: datetime | None = None,
    ) -> list[RankedMemory]:
        """Rank memories using weighted composite score.

        Formula::

            score = w_sim * similarity + w_rec * recency + w_imp * importance

        Args:
            candidates: Pairs of (record, similarity).
            now: Reference time for recency (defaults to UTC now).

        Returns:
            Descending ranked list.
        """
        ref = now or datetime.now(timezone.utc)
        ranked: list[RankedMemory] = []
        for record, similarity in candidates:
            recency = self._recency_score(record.updated_at, ref)
            importance = self._normalize_importance(record.importance)
            score = (
                self.config.similarity_weight * similarity
                + self.config.recency_weight * recency
                + self.config.importance_weight * importance
            )
            ranked.append(
                RankedMemory(
                    record=record,
                    similarity=similarity,
                    recency=recency,
                    importance=importance,
                    score=score,
                )
            )
        ranked.sort(key=lambda m: (-m.score, -m.similarity, m.record.id or 0))
        return ranked

    def _recency_score(self, updated_at: datetime, now: datetime) -> float:
        """Exponential decay recency in [0, 1]."""
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (now - updated_at).total_seconds() / 86400.0)
        half_life = max(1.0, self.config.recency_half_life_days)
        return math.exp(-math.log(2) * age_days / half_life)

    @staticmethod
    def _normalize_importance(value: float) -> float:
        """Clamp importance to [0, 1]."""
        return max(0.0, min(1.0, float(value)))
