"""Data models for the user profile engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass
class ProfileAttribute:
    """A resolved profile attribute with provenance and confidence."""

    value: Any = None
    confidence: float = 0.0
    source_memory_id: int | None = None
    source_kind: str = "unknown"
    updated_at: datetime = field(default_factory=utc_now)
    explicit: bool = True
    verified: bool = False
    version: int = 1

    def is_set(self) -> bool:
        """Return True when the attribute has a meaningful value."""
        if self.value is None:
            return False
        if isinstance(self.value, str):
            return bool(self.value.strip())
        if isinstance(self.value, list):
            return bool(self.value)
        if isinstance(self.value, dict):
            return bool(self.value)
        return True

    def to_dict(self) -> dict[str, Any]:
        """Serialize attribute."""
        return {
            "value": self.value,
            "confidence": round(self.confidence, 6),
            "source_memory_id": self.source_memory_id,
            "source_kind": self.source_kind,
            "updated_at": self.updated_at.isoformat(),
            "explicit": self.explicit,
            "verified": self.verified,
            "version": self.version,
        }


@dataclass
class BodyMetrics:
    """Structured body metrics."""

    height_cm: ProfileAttribute = field(default_factory=ProfileAttribute)
    weight_kg: ProfileAttribute = field(default_factory=ProfileAttribute)
    body_fat_percent: ProfileAttribute = field(default_factory=ProfileAttribute)
    age: ProfileAttribute = field(default_factory=ProfileAttribute)
    gender: ProfileAttribute = field(default_factory=ProfileAttribute)
    activity_level: ProfileAttribute = field(default_factory=ProfileAttribute)

    def to_dict(self) -> dict[str, Any]:
        """Serialize body metrics."""
        return {
            "height_cm": self.height_cm.to_dict(),
            "weight_kg": self.weight_kg.to_dict(),
            "body_fat_percent": self.body_fat_percent.to_dict(),
            "age": self.age.to_dict(),
            "gender": self.gender.to_dict(),
            "activity_level": self.activity_level.to_dict(),
        }


@dataclass
class UserProfile:
    """Top-level user profile aggregated from memory."""

    user_id: str
    basic_information: dict[str, ProfileAttribute] = field(default_factory=dict)
    fitness_goal: ProfileAttribute = field(default_factory=ProfileAttribute)
    body_metrics: BodyMetrics = field(default_factory=BodyMetrics)
    experience: ProfileAttribute = field(default_factory=ProfileAttribute)
    workout_preferences: dict[str, ProfileAttribute] = field(default_factory=dict)
    nutrition_preferences: dict[str, ProfileAttribute] = field(default_factory=dict)
    equipment: list[ProfileAttribute] = field(default_factory=list)
    injuries: list[ProfileAttribute] = field(default_factory=list)
    restrictions: list[ProfileAttribute] = field(default_factory=list)
    supplements: list[ProfileAttribute] = field(default_factory=list)
    schedule: ProfileAttribute = field(default_factory=ProfileAttribute)
    favorite_exercises: list[ProfileAttribute] = field(default_factory=list)
    disliked_exercises: list[ProfileAttribute] = field(default_factory=list)
    current_program: ProfileAttribute = field(default_factory=ProfileAttribute)
    last_updated: datetime = field(default_factory=utc_now)
    confidence_score: float = 0.0
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize profile into nested dictionaries."""
        return {
            "user_id": self.user_id,
            "basic_information": {k: v.to_dict() for k, v in self.basic_information.items()},
            "fitness_goal": self.fitness_goal.to_dict(),
            "body_metrics": self.body_metrics.to_dict(),
            "experience": self.experience.to_dict(),
            "workout_preferences": {
                k: v.to_dict() for k, v in self.workout_preferences.items()
            },
            "nutrition_preferences": {
                k: v.to_dict() for k, v in self.nutrition_preferences.items()
            },
            "equipment": [item.to_dict() for item in self.equipment],
            "injuries": [item.to_dict() for item in self.injuries],
            "restrictions": [item.to_dict() for item in self.restrictions],
            "supplements": [item.to_dict() for item in self.supplements],
            "schedule": self.schedule.to_dict(),
            "favorite_exercises": [item.to_dict() for item in self.favorite_exercises],
            "disliked_exercises": [item.to_dict() for item in self.disliked_exercises],
            "current_program": self.current_program.to_dict(),
            "last_updated": self.last_updated.isoformat(),
            "confidence_score": round(self.confidence_score, 6),
            "version": self.version,
        }

    def export_compact(self) -> dict[str, Any]:
        """Export a compact JSON-friendly profile view."""
        return {
            "goal": self.fitness_goal.value,
            "weight": self.body_metrics.weight_kg.value,
            "height": self.body_metrics.height_cm.value,
            "experience": self.experience.value,
            "schedule": self.schedule.value,
            "equipment": [item.value for item in self.equipment if item.is_set()],
            "injury": [item.value for item in self.injuries if item.is_set()],
            "restrictions": [item.value for item in self.restrictions if item.is_set()],
            "supplements": [item.value for item in self.supplements if item.is_set()],
            "current_program": self.current_program.value,
            "confidence_score": round(self.confidence_score, 6),
            "version": self.version,
        }


@dataclass
class ProfileSnapshot:
    """Rendered compact profile used in prompts."""

    user_id: str
    text: str
    token_estimate: int
    version: int
    confidence_score: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize snapshot."""
        return asdict(self)


@dataclass
class ProfileUpdateResult:
    """Result of a profile update operation."""

    profile: UserProfile
    changed_fields: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize update result."""
        return {
            "profile": self.profile.to_dict(),
            "changed_fields": list(self.changed_fields),
            "latency_ms": round(self.latency_ms, 6),
            "version": self.version,
        }
