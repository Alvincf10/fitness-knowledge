"""Conversation context enrichment for follow-up questions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class Turn:
    role: str  # user | assistant
    content: str


@dataclass
class ConversationState:
    """Rolling chat history used to enrich follow-up retrieval queries."""

    turns: list[Turn] = field(default_factory=list)
    max_history: int = 4

    def add(self, role: str, content: str) -> None:
        text = (content or "").strip()
        if not text:
            return
        self.turns.append(Turn(role=role, content=text))
        # Keep last N user+assistant pairs roughly
        max_turns = max(2, self.max_history * 2)
        if len(self.turns) > max_turns:
            self.turns = self.turns[-max_turns:]

    def clear(self) -> None:
        self.turns.clear()


_FOLLOWUP_MARKERS = {
    "how much",
    "how many",
    "what about",
    "and the",
    "also",
    "same",
    "that",
    "it",
    "this",
    "those",
    "berapa",
    "bagaimana",
    "lalu",
    "terus",
    "juga",
    "itu",
}


def looks_like_followup(query: str) -> bool:
    q = (query or "").strip().lower()
    if len(q.split()) <= 6:
        return True
    return any(m in q for m in _FOLLOWUP_MARKERS)


def enrich_query_with_history(
    query: str,
    history: Sequence[Turn] | ConversationState | None,
    *,
    max_history: int = 4,
    enabled: bool = True,
) -> str:
    """Build a retrieval query that includes prior conversational context.

    Concatenates prior user turns so follow-ups like "How much should I take?"
    resolve against the earlier topic (e.g. creatine). No translation.
    """
    q = (query or "").strip()
    if not enabled or not history:
        return q

    if isinstance(history, ConversationState):
        turns = list(history.turns)
        max_history = history.max_history or max_history
    else:
        turns = list(history)

    if not turns:
        return q

    user_turns = [t.content for t in turns if t.role == "user"][-max_history:]
    prior_users = [u for u in user_turns if u.strip() and u.strip().lower() != q.lower()]
    if not prior_users and not looks_like_followup(q):
        return q
    if not prior_users:
        return q

    # Compact enrichment: prior topics + current (avoids meta words that break grounding)
    prior = " ".join(prior_users[-max_history:])
    return f"{prior} {q}".strip()
