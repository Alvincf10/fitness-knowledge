"""Profile updater built on top of memory records."""

from __future__ import annotations

import logging
import re
import time
from typing import Iterable

from memory.models import MemoryRecord

from .confidence import ProfileConfidenceScorer
from .models import BodyMetrics, ProfileAttribute, ProfileUpdateResult, UserProfile, utc_now
from .resolver import ProfileConflictResolver
from .validator import ProfileValidator

logger = logging.getLogger(__name__)


class ProfileUpdater:
    """Apply memory updates to a structured user profile."""

    def __init__(
        self,
        *,
        resolver: ProfileConflictResolver | None = None,
        confidence: ProfileConfidenceScorer | None = None,
        validator: ProfileValidator | None = None,
    ) -> None:
        self.resolver = resolver or ProfileConflictResolver()
        self.confidence = confidence or ProfileConfidenceScorer()
        self.validator = validator or ProfileValidator()

    def build_profile(self, user_id: str, memories: Iterable[MemoryRecord]) -> UserProfile:
        """Build a profile from all user memories."""
        profile = UserProfile(user_id=user_id)
        changed: set[str] = set()
        for memory in sorted(memories, key=lambda item: item.updated_at):
            changed.update(self.apply_memory(profile, memory))
        profile.last_updated = utc_now()
        profile.confidence_score = self.confidence.profile_score(self._all_attributes(profile))
        self._ensure_version(profile)
        return profile

    def update_profile(
        self,
        profile: UserProfile,
        memories: Iterable[MemoryRecord],
    ) -> ProfileUpdateResult:
        """Update an existing profile with new memory records."""
        t0 = time.perf_counter()
        changed: set[str] = set()
        for memory in sorted(memories, key=lambda item: item.updated_at):
            changed.update(self.apply_memory(profile, memory))
        profile.last_updated = utc_now()
        profile.confidence_score = self.confidence.profile_score(self._all_attributes(profile))
        if changed:
            profile.version += 1
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return ProfileUpdateResult(
            profile=profile,
            changed_fields=sorted(changed),
            latency_ms=latency_ms,
            version=profile.version,
        )

    def apply_memory(self, profile: UserProfile, memory: MemoryRecord) -> set[str]:
        """Apply a single memory record to the profile."""
        category = memory.category.strip().lower()
        value = self._parse_value(memory.content)
        attr = self._attribute_from_memory(memory, value)
        changed: set[str] = set()

        if category == "goal":
            profile.fitness_goal = self._resolve(profile.fitness_goal, attr)
            changed.add("fitness_goal")
        elif category == "experience":
            profile.experience = self._resolve(profile.experience, attr)
            changed.add("experience")
        elif category == "height":
            profile.body_metrics.height_cm = self._resolve(profile.body_metrics.height_cm, attr)
            changed.add("body_metrics.height_cm")
        elif category == "weight":
            profile.body_metrics.weight_kg = self._resolve(profile.body_metrics.weight_kg, attr)
            changed.add("body_metrics.weight_kg")
        elif category == "age":
            profile.body_metrics.age = self._resolve(profile.body_metrics.age, attr)
            changed.add("body_metrics.age")
        elif category == "schedule":
            profile.schedule = self._resolve(profile.schedule, attr)
            profile.workout_preferences["schedule"] = profile.schedule
            changed.update({"schedule", "workout_preferences.schedule"})
        elif category == "workout_split":
            profile.current_program = self._resolve(profile.current_program, attr)
            profile.workout_preferences["split"] = profile.current_program
            changed.update({"current_program", "workout_preferences.split"})
        elif category == "diet":
            profile.nutrition_preferences["diet"] = self._resolve(
                profile.nutrition_preferences.get("diet", ProfileAttribute()),
                attr,
            )
            changed.add("nutrition_preferences.diet")
        elif category == "equipment":
            self._append_unique(profile.equipment, attr)
            changed.add("equipment")
        elif category == "injury":
            self._append_unique(profile.injuries, attr)
            changed.add("injuries")
        elif category == "restriction":
            self._append_unique(profile.restrictions, attr)
            changed.add("restrictions")
        elif category == "supplement":
            self._append_unique(profile.supplements, attr)
            changed.add("supplements")
        elif category == "favorite_exercise":
            self._append_unique(profile.favorite_exercises, attr)
            changed.add("favorite_exercises")

        errors = self.validator.validate(profile)
        if errors:
            logger.debug("Profile validation issues for %s: %s", profile.user_id, errors)
        return changed

    def _attribute_from_memory(self, memory: MemoryRecord, value: object) -> ProfileAttribute:
        explicit = True
        verified = memory.importance >= 0.85
        age_days = self.confidence.age_days(memory.updated_at)
        confidence = self.confidence.score(
            explicit=explicit,
            verified=verified,
            importance=memory.importance,
            age_days=age_days,
        )
        return self.resolver.from_memory(
            memory,
            value=value,
            confidence=confidence,
            explicit=explicit,
            verified=verified,
            version=1,
        )

    def _resolve(self, current: ProfileAttribute, candidate: ProfileAttribute) -> ProfileAttribute:
        chosen = self.resolver.choose(current, candidate)
        if chosen is candidate and current.is_set():
            chosen.version = current.version + 1
        return chosen

    @staticmethod
    def _parse_value(content: str) -> object:
        _, _, raw = content.partition(":")
        value = raw.strip() if raw.strip() else content.strip()
        number = re.fullmatch(r"-?\d+(?:\.\d+)?", value)
        if number:
            numeric = float(value)
            return int(numeric) if numeric.is_integer() else numeric
        return value

    @staticmethod
    def _append_unique(items: list[ProfileAttribute], candidate: ProfileAttribute) -> None:
        norm = str(candidate.value).strip().lower()
        for idx, item in enumerate(items):
            if str(item.value).strip().lower() == norm:
                items[idx] = candidate if candidate.confidence >= item.confidence else item
                return
        items.append(candidate)

    @staticmethod
    def _all_attributes(profile: UserProfile) -> list[ProfileAttribute]:
        attrs = [
            profile.fitness_goal,
            profile.body_metrics.height_cm,
            profile.body_metrics.weight_kg,
            profile.body_metrics.body_fat_percent,
            profile.body_metrics.age,
            profile.body_metrics.gender,
            profile.body_metrics.activity_level,
            profile.experience,
            profile.schedule,
            profile.current_program,
        ]
        attrs.extend(profile.basic_information.values())
        attrs.extend(profile.workout_preferences.values())
        attrs.extend(profile.nutrition_preferences.values())
        attrs.extend(profile.equipment)
        attrs.extend(profile.injuries)
        attrs.extend(profile.restrictions)
        attrs.extend(profile.supplements)
        attrs.extend(profile.favorite_exercises)
        attrs.extend(profile.disliked_exercises)
        return attrs

    @staticmethod
    def _ensure_version(profile: UserProfile) -> None:
        profile.version = max(1, profile.version)
