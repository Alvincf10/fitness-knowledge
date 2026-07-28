"""Data models for the conversation memory engine."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Sequence


def utc_now() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


class MemoryCategory(str, Enum):
    """Long-term memory categories for fitness user profiles."""

    GOAL = "goal"
    EXPERIENCE = "experience"
    HEIGHT = "height"
    WEIGHT = "weight"
    AGE = "age"
    INJURY = "injury"
    EQUIPMENT = "equipment"
    FAVORITE_EXERCISE = "favorite_exercise"
    WORKOUT_SPLIT = "workout_split"
    SCHEDULE = "schedule"
    SUPPLEMENT = "supplement"
    DIET = "diet"
    RESTRICTION = "restriction"
    ACHIEVEMENT = "achievement"
    SESSION = "session"

    @classmethod
    def from_str(cls, value: str) -> MemoryCategory:
        """Parse category string, defaulting to SESSION for unknown values."""
        try:
            return cls(value.lower().strip())
        except ValueError:
            return cls.SESSION


@dataclass(frozen=True)
class ExtractedMemory:
    """A fact extracted from a user message."""

    category: str
    value: str
    content: str
    importance: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return asdict(self)


@dataclass
class MemoryRecord:
    """Persisted long-term memory row."""

    id: int | None
    user_id: str
    category: str
    content: str
    embedding: list[float] | None = None
    importance: float = 0.5
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for logging and evaluation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category": self.category,
            "content": self.content,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class RankedMemory:
    """Memory candidate with retrieval scores."""

    record: MemoryRecord
    similarity: float = 0.0
    recency: float = 0.0
    importance: float = 0.0
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize ranked result."""
        data = self.record.to_dict()
        data.update(
            {
                "similarity": round(self.similarity, 6),
                "recency": round(self.recency, 6),
                "importance": round(self.importance, 6),
                "score": round(self.score, 6),
            }
        )
        return data


@dataclass
class ConversationSummary:
    """Structured summary of a conversation."""

    current_goal: str = ""
    current_progress: str = ""
    important_facts: list[str] = field(default_factory=list)
    recent_changes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize summary sections."""
        return asdict(self)

    def render(self) -> str:
        """Render summary as markdown-like text."""
        lines = [
            "## Conversation Summary",
            "",
            f"**Current Goal:** {self.current_goal or 'Not specified'}",
            f"**Current Progress:** {self.current_progress or 'Not specified'}",
            "",
            "**Important Facts:**",
        ]
        if self.important_facts:
            lines.extend(f"- {fact}" for fact in self.important_facts)
        else:
            lines.append("- None recorded")
        lines.extend(["", "**Recent Changes:**"])
        if self.recent_changes:
            lines.extend(f"- {change}" for change in self.recent_changes)
        else:
            lines.append("- None")
        return "\n".join(lines)


@dataclass
class BuiltMemoryContext:
    """Formatted prompt context combining memory and knowledge."""

    summary: ConversationSummary
    memories: list[RankedMemory]
    knowledge_text: str
    question: str
    text: str
    token_estimate: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize built context."""
        return {
            "summary": self.summary.to_dict(),
            "memories": [m.to_dict() for m in self.memories],
            "knowledge_text": self.knowledge_text,
            "question": self.question,
            "text": self.text,
            "token_estimate": self.token_estimate,
        }


@dataclass
class MemoryConfig:
    """Runtime configuration for the memory engine."""

    db_path: str = "data/memory.db"
    embedding_provider: str = "hash"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    top_k: int = 5
    similarity_weight: float = 0.5
    recency_weight: float = 0.3
    importance_weight: float = 0.2
    recency_half_life_days: float = 30.0
    summary_max_turns: int = 20
    summary_trigger_turns: int = 12
    default_importance: float = 0.5
    chars_per_token: float = 4.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryConfig:
        """Build config from a mapping."""
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})

    def to_dict(self) -> dict[str, Any]:
        """Serialize config."""
        return asdict(self)


def embedding_to_blob(vector: Sequence[float]) -> bytes:
    """Pack embedding floats into bytes for SQLite storage."""
    import struct

    return struct.pack(f"{len(vector)}f", *vector)


def blob_to_embedding(blob: bytes) -> list[float]:
    """Unpack embedding bytes from SQLite."""
    import struct

    count = len(blob) // 4
    return list(struct.unpack(f"{count}f", blob))


def dumps_metadata(data: dict[str, Any]) -> str:
    """JSON-encode metadata."""
    return json.dumps(data, ensure_ascii=False)
