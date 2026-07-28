"""Short-term session memory for active conversations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SessionTurn:
    """A single conversation turn."""

    role: str
    content: str
    timestamp: datetime = field(default_factory=_utc_now)


@dataclass
class ConversationSession:
    """In-memory short-term session state."""

    user_id: str
    turns: list[SessionTurn] = field(default_factory=list)
    facts: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)

    def add_turn(self, role: str, content: str) -> None:
        """Append a conversation turn."""
        text = (content or "").strip()
        if not text:
            return
        self.turns.append(SessionTurn(role=role, content=text))

    def set_fact(self, key: str, value: str) -> None:
        """Store a short-term session fact."""
        self.facts[key.strip()] = value.strip()

    def get_fact(self, key: str, default: str = "") -> str:
        """Read a session fact."""
        return self.facts.get(key, default)

    def clear(self) -> None:
        """Reset session turns and facts."""
        self.turns.clear()
        self.facts.clear()

    def last_user_message(self) -> str:
        """Return the most recent user message."""
        for turn in reversed(self.turns):
            if turn.role == "user":
                return turn.content
        return ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize session state."""
        return {
            "user_id": self.user_id,
            "turns": [{"role": t.role, "content": t.content} for t in self.turns],
            "facts": dict(self.facts),
            "metadata": dict(self.metadata),
        }
