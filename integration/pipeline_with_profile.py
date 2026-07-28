"""Profile-first integration wrapper for the RAG pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from memory.manager import MemoryManager
from profile.engine import UserProfileEngine


@dataclass
class ProfileAugmentedContext:
    """Profile-first retrieval payload."""

    profile_snapshot: str
    conversation_summary: str
    relevant_memories: list[str]
    knowledge_query: str
    prompt_context: str
    latency_ms: float
    extras: dict[str, Any] = field(default_factory=dict)


def build_profile_first_context(
    profile_engine: UserProfileEngine,
    memory_manager: MemoryManager,
    user_id: str,
    question: str,
    *,
    knowledge_text: str = "",
    top_k_memories: int = 3,
) -> ProfileAugmentedContext:
    """Build profile-first prompt context without changing prior phases."""
    retrieved = profile_engine.retrieve_with_profile_priority(user_id, question, top_k=top_k_memories)
    snapshot = retrieved["snapshot"]
    summary = retrieved["summary"]
    memories = retrieved["memories"]
    relevant_memories = [item.record.content for item in memories]
    knowledge_query = " ".join(
        part
        for part in [
            str(snapshot.text).replace("\n", " "),
            " ".join(relevant_memories),
            question.strip(),
        ]
        if part.strip()
    )
    prompt_context = "\n\n".join(
        [
            snapshot.text,
            summary.render(),
            "## Relevant Memories\n\n" + ("\n".join(f"- {item}" for item in relevant_memories) or "- None"),
            "## Knowledge Context\n\n" + (knowledge_text.strip() or "Not provided"),
            "## Current Question\n\n" + question.strip(),
            "Answer using all available context.",
        ]
    )
    return ProfileAugmentedContext(
        profile_snapshot=snapshot.text,
        conversation_summary=summary.render(),
        relevant_memories=relevant_memories,
        knowledge_query=knowledge_query,
        prompt_context=prompt_context,
        latency_ms=float(retrieved["latency_ms"]),
        extras={"profile_version": snapshot.version, "confidence": snapshot.confidence_score},
    )
