"""Heuristic conversation summarization (no LLM)."""

from __future__ import annotations

import logging
from typing import Sequence

from conversation.session import SessionTurn

from .models import ConversationSummary, MemoryCategory, MemoryRecord

logger = logging.getLogger(__name__)


class ConversationSummarizer:
    """Summarize conversation history and stored memories."""

    def summarize(
        self,
        turns: Sequence[SessionTurn],
        memories: Sequence[MemoryRecord],
        *,
        session_facts: dict[str, str] | None = None,
    ) -> ConversationSummary:
        """Build a structured summary from turns and long-term memories.

        Args:
            turns: Recent conversation turns.
            memories: User long-term memories.
            session_facts: Short-term session key-value facts.

        Returns:
            Structured :class:`ConversationSummary`.
        """
        session_facts = session_facts or {}
        by_category: dict[str, list[MemoryRecord]] = {}
        for mem in memories:
            by_category.setdefault(mem.category, []).append(mem)

        goal = self._latest_value(by_category.get(MemoryCategory.GOAL.value, []))
        progress = self._build_progress(by_category, session_facts)
        facts = self._important_facts(by_category, session_facts)
        changes = self._recent_changes(turns, memories)

        return ConversationSummary(
            current_goal=goal,
            current_progress=progress,
            important_facts=facts,
            recent_changes=changes,
        )

    def should_summarize(self, turn_count: int, *, trigger: int = 12) -> bool:
        """Return True when history exceeds summarization threshold."""
        return turn_count >= trigger

    @staticmethod
    def _latest_value(records: Sequence[MemoryRecord]) -> str:
        if not records:
            return ""
        latest = max(records, key=lambda r: r.updated_at)
        return latest.content.split(":", 1)[-1].strip()

    def _build_progress(
        self,
        by_category: dict[str, list[MemoryRecord]],
        session_facts: dict[str, str],
    ) -> str:
        parts: list[str] = []
        weight = self._latest_value(by_category.get(MemoryCategory.WEIGHT.value, []))
        achievement = self._latest_value(by_category.get(MemoryCategory.ACHIEVEMENT.value, []))
        if weight:
            parts.append(f"Current weight: {weight} kg")
        if achievement:
            parts.append(f"Latest achievement: {achievement}")
        if session_facts.get("last_workout"):
            parts.append(f"Last workout: {session_facts['last_workout']}")
        return "; ".join(parts)

    def _important_facts(
        self,
        by_category: dict[str, list[MemoryRecord]],
        session_facts: dict[str, str],
    ) -> list[str]:
        priority = [
            MemoryCategory.GOAL.value,
            MemoryCategory.RESTRICTION.value,
            MemoryCategory.INJURY.value,
            MemoryCategory.HEIGHT.value,
            MemoryCategory.WEIGHT.value,
            MemoryCategory.WORKOUT_SPLIT.value,
            MemoryCategory.SCHEDULE.value,
            MemoryCategory.DIET.value,
            MemoryCategory.SUPPLEMENT.value,
            MemoryCategory.EQUIPMENT.value,
        ]
        facts: list[str] = []
        for cat in priority:
            records = by_category.get(cat, [])
            if records:
                latest = max(records, key=lambda r: r.updated_at)
                facts.append(latest.content)
        for key, value in sorted(session_facts.items()):
            facts.append(f"session: {key}={value}")
        return facts[:12]

    def _recent_changes(
        self,
        turns: Sequence[SessionTurn],
        memories: Sequence[MemoryRecord],
    ) -> list[str]:
        changes: list[str] = []
        user_turns = [t.content for t in turns if t.role == "user"][-5:]
        for turn in user_turns:
            snippet = turn.strip()
            if len(snippet) > 120:
                snippet = snippet[:117] + "..."
            changes.append(snippet)
        if not changes and memories:
            latest = sorted(memories, key=lambda m: m.updated_at, reverse=True)[:3]
            changes = [m.content for m in latest]
        return changes[:5]
