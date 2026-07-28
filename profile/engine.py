"""High-level user profile engine built on top of memory."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from memory.manager import MemoryManager
from memory.models import MemoryRecord, RankedMemory

from .models import ProfileSnapshot, ProfileUpdateResult, UserProfile
from .snapshot import ProfileSnapshotBuilder
from .updater import ProfileUpdater
from .validator import ProfileValidator

logger = logging.getLogger(__name__)


class UserProfileEngine:
    """Build, update, persist, and retrieve user profiles."""

    def __init__(
        self,
        memory_manager: MemoryManager,
        *,
        updater: ProfileUpdater | None = None,
        validator: ProfileValidator | None = None,
        snapshot_builder: ProfileSnapshotBuilder | None = None,
    ) -> None:
        self.memory_manager = memory_manager
        self.updater = updater or ProfileUpdater()
        self.validator = validator or ProfileValidator()
        self.snapshot_builder = snapshot_builder or ProfileSnapshotBuilder()
        self._profiles: dict[str, UserProfile] = {}
        self._history: dict[str, list[dict[str, object]]] = {}

    def build_profile(self, user_id: str) -> UserProfile:
        """Build a profile from all stored memories for a user."""
        memories = self.memory_manager.storage.get_by_user(user_id)
        profile = self.updater.build_profile(user_id, memories)
        self._profiles[user_id] = profile
        self._record_version(profile)
        return profile

    def get_profile(self, user_id: str, *, rebuild: bool = False) -> UserProfile:
        """Return the current profile, building it if needed."""
        if rebuild or user_id not in self._profiles:
            return self.build_profile(user_id)
        return self._profiles[user_id]

    def update_from_memories(
        self,
        user_id: str,
        memories: list[MemoryRecord],
    ) -> ProfileUpdateResult:
        """Update cached profile from new memories."""
        profile = self.get_profile(user_id)
        result = self.updater.update_profile(profile, memories)
        self._profiles[user_id] = result.profile
        if result.changed_fields:
            self._record_version(result.profile)
        return result

    def update_from_message(self, user_id: str, message: str) -> ProfileUpdateResult:
        """Update memory and profile from a new user message."""
        memories = self.memory_manager.process_user_message(user_id, message)
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id=user_id)
        return self.update_from_memories(user_id, memories)

    def snapshot(self, user_id: str) -> ProfileSnapshot:
        """Generate compact prompt snapshot."""
        profile = self.get_profile(user_id)
        return self.snapshot_builder.build(
            profile,
            chars_per_token=self.memory_manager.config.chars_per_token,
        )

    def retrieve_with_profile_priority(
        self,
        user_id: str,
        query: str,
        *,
        top_k: int | None = None,
    ) -> dict[str, object]:
        """Return profile-first retrieval context."""
        profile = self.get_profile(user_id)
        snapshot = self.snapshot(user_id)
        memories, latency_ms = self.memory_manager.retrieve_memory(user_id, query, top_k=top_k)
        summary = self.memory_manager.summarize(user_id)
        return {
            "profile": profile,
            "snapshot": snapshot,
            "memories": memories,
            "summary": summary,
            "latency_ms": latency_ms,
        }

    def save_profile(self, user_id: str, path: str | Path) -> Path:
        """Export compact profile JSON to disk."""
        profile = self.get_profile(user_id)
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(profile.export_compact(), indent=2), encoding="utf-8")
        return output

    def load_profile(self, user_id: str, path: str | Path) -> UserProfile:
        """Load a compact profile JSON into a cached profile."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        profile = UserProfile(user_id=user_id)
        if data.get("goal") is not None:
            profile.fitness_goal.value = data["goal"]
        if data.get("weight") is not None:
            profile.body_metrics.weight_kg.value = data["weight"]
        if data.get("height") is not None:
            profile.body_metrics.height_cm.value = data["height"]
        if data.get("experience") is not None:
            profile.experience.value = data["experience"]
        if data.get("schedule") is not None:
            profile.schedule.value = data["schedule"]
        if data.get("current_program") is not None:
            profile.current_program.value = data["current_program"]
        profile.version = int(data.get("version", 1))
        self._profiles[user_id] = profile
        self._record_version(profile)
        return profile

    def profile_errors(self, user_id: str) -> list[str]:
        """Return validation errors for a user's current profile."""
        return self.validator.validate(self.get_profile(user_id))

    def version_history(self, user_id: str) -> list[dict[str, object]]:
        """Return saved version snapshots for a user."""
        return list(self._history.get(user_id, []))

    def _record_version(self, profile: UserProfile) -> None:
        snapshot = {
            "version": f"v{profile.version}",
            "updated_at": profile.last_updated.isoformat(),
            "profile": profile.export_compact(),
        }
        self._history.setdefault(profile.user_id, []).append(snapshot)
