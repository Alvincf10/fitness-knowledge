"""Validation rules for user profiles."""

from __future__ import annotations

from typing import Iterable

from .models import ProfileAttribute, UserProfile


class ProfileValidator:
    """Validate user profile data."""

    VALID_GOALS = {
        "cutting",
        "bulking",
        "maintenance",
        "strength",
        "hypertrophy",
        "endurance",
        "fat_loss",
        "recomp",
    }

    def validate(self, profile: UserProfile) -> list[str]:
        """Return validation errors for a profile."""
        errors: list[str] = []
        errors.extend(self._validate_numeric("height_cm", profile.body_metrics.height_cm, 50, 300))
        errors.extend(self._validate_numeric("weight_kg", profile.body_metrics.weight_kg, 20, 500))
        errors.extend(self._validate_numeric("age", profile.body_metrics.age, 10, 120))

        goal = profile.fitness_goal.value
        if goal is not None and str(goal).strip():
            normalized = str(goal).strip().lower()
            if normalized not in self.VALID_GOALS:
                errors.append(f"invalid goal: {goal}")

        errors.extend(self._validate_list("equipment", profile.equipment))
        errors.extend(self._validate_list("injuries", profile.injuries))
        errors.extend(self._validate_list("restrictions", profile.restrictions))
        errors.extend(self._validate_list("supplements", profile.supplements))
        return errors

    @staticmethod
    def _validate_numeric(
        name: str,
        attr: ProfileAttribute,
        min_value: float,
        max_value: float,
    ) -> list[str]:
        if not attr.is_set():
            return []
        try:
            value = float(attr.value)
        except (TypeError, ValueError):
            return [f"{name} must be numeric"]
        if value < min_value or value > max_value:
            return [f"{name} out of range: {value}"]
        return []

    @staticmethod
    def _validate_list(name: str, attrs: Iterable[ProfileAttribute]) -> list[str]:
        errors: list[str] = []
        for attr in attrs:
            if attr.value is None:
                errors.append(f"{name} contains empty value")
            elif isinstance(attr.value, str) and not attr.value.strip():
                errors.append(f"{name} contains blank value")
        return errors
