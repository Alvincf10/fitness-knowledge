"""Confidence scoring for profile attributes."""

from __future__ import annotations

from datetime import datetime, timezone

from .models import ProfileAttribute


class ProfileConfidenceScorer:
    """Compute confidence values for resolved profile attributes."""

    def score(
        self,
        *,
        explicit: bool,
        verified: bool,
        importance: float,
        age_days: float,
        consistency_bonus: float = 0.0,
    ) -> float:
        """Return a confidence score in ``[0, 1]``."""
        base = 0.45
        if explicit:
            base += 0.18
        if verified:
            base += 0.12
        base += max(0.0, min(1.0, importance)) * 0.18
        recency = max(0.0, 1.0 - min(age_days, 365.0) / 365.0)
        base += recency * 0.05
        base += max(0.0, min(0.1, consistency_bonus))
        return max(0.0, min(0.99, base))

    def profile_score(self, attributes: list[ProfileAttribute]) -> float:
        """Compute aggregate profile confidence."""
        scored = [attr.confidence for attr in attributes if attr.is_set()]
        if not scored:
            return 0.0
        return round(sum(scored) / len(scored), 6)

    @staticmethod
    def age_days(updated_at: datetime, now: datetime | None = None) -> float:
        """Return age in days for a timestamp."""
        ref = now or datetime.now(timezone.utc)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        return max(0.0, (ref - updated_at).total_seconds() / 86400.0)
