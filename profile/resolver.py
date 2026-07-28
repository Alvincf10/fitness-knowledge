"""Conflict resolution for profile attributes."""

from __future__ import annotations

from dataclasses import replace

from memory.models import MemoryRecord

from .models import ProfileAttribute


class ProfileConflictResolver:
    """Resolve attribute conflicts from competing memory evidence."""

    def choose(
        self,
        current: ProfileAttribute | None,
        candidate: ProfileAttribute,
    ) -> ProfileAttribute:
        """Choose the stronger attribute according to profile rules."""
        if current is None or not current.is_set():
            return candidate

        if self._is_newer(candidate, current):
            if candidate.confidence >= current.confidence:
                return candidate
            if candidate.explicit and not current.explicit:
                return candidate
            if candidate.verified and not current.verified:
                return candidate

        if candidate.verified and not current.verified:
            return candidate
        if candidate.explicit and not current.explicit:
            return candidate
        if candidate.confidence > current.confidence:
            return candidate
        return current

    @staticmethod
    def from_memory(
        memory: MemoryRecord,
        *,
        value: object,
        confidence: float,
        explicit: bool = True,
        verified: bool = False,
        source_kind: str = "memory",
        version: int = 1,
    ) -> ProfileAttribute:
        """Build a profile attribute from a memory record."""
        return ProfileAttribute(
            value=value,
            confidence=confidence,
            source_memory_id=memory.id,
            source_kind=source_kind,
            updated_at=memory.updated_at,
            explicit=explicit,
            verified=verified,
            version=version,
        )

    @staticmethod
    def _is_newer(candidate: ProfileAttribute, current: ProfileAttribute) -> bool:
        return candidate.updated_at >= current.updated_at
