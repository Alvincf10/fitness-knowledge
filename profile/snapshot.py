"""Snapshot generation for compact profile prompts."""

from __future__ import annotations

from .models import ProfileSnapshot, UserProfile


class ProfileSnapshotBuilder:
    """Render compact user profile snapshots."""

    def build(self, profile: UserProfile, *, chars_per_token: float = 4.0) -> ProfileSnapshot:
        """Build a compact profile snapshot."""
        lines = [
            "## User Profile",
            "",
            f"Goal: {profile.fitness_goal.value or 'Unknown'}",
            f"Experience: {profile.experience.value or 'Unknown'}",
            f"Workout: {self._first_pref(profile.workout_preferences) or 'Unknown'}",
            f"Gym Time: {profile.schedule.value or 'Unknown'}",
            f"Weight: {self._fmt(profile.body_metrics.weight_kg.value, 'kg')}",
            f"Height: {self._fmt(profile.body_metrics.height_cm.value, 'cm')}",
            f"Equipment: {self._join_values(profile.equipment) or 'Unknown'}",
            f"Injury: {self._join_values(profile.injuries) or 'None'}",
            f"Restrictions: {self._join_values(profile.restrictions) or 'None'}",
            f"Current Program: {profile.current_program.value or 'Unknown'}",
        ]
        text = "\n".join(lines)
        return ProfileSnapshot(
            user_id=profile.user_id,
            text=text,
            token_estimate=int(len(text) / chars_per_token),
            version=profile.version,
            confidence_score=profile.confidence_score,
        )

    @staticmethod
    def _join_values(items: list) -> str:
        values = [str(item.value) for item in items if item.is_set()]
        return ", ".join(values)

    @staticmethod
    def _fmt(value: object, unit: str) -> str:
        if value is None or value == "":
            return "Unknown"
        return f"{value} {unit}"

    @staticmethod
    def _first_pref(preferences: dict) -> str:
        for key, attr in preferences.items():
            if attr.is_set():
                return str(attr.value)
        return ""
