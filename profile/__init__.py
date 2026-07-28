"""User profile engine."""

from __future__ import annotations

from .confidence import ProfileConfidenceScorer
from .engine import UserProfileEngine
from .models import (
    BodyMetrics,
    ProfileAttribute,
    ProfileSnapshot,
    ProfileUpdateResult,
    UserProfile,
)
from .resolver import ProfileConflictResolver
from .snapshot import ProfileSnapshotBuilder
from .updater import ProfileUpdater
from .validator import ProfileValidator

__all__ = [
    "BodyMetrics",
    "ProfileAttribute",
    "ProfileConfidenceScorer",
    "ProfileConflictResolver",
    "ProfileSnapshot",
    "ProfileSnapshotBuilder",
    "ProfileUpdateResult",
    "ProfileUpdater",
    "ProfileValidator",
    "UserProfile",
    "UserProfileEngine",
]
