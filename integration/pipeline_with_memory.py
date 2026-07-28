"""Backward-compatible integration between memory engine and RAG pipeline.

This module does **not** modify Phase 1–5.75 components. It wraps the existing
``RagPipeline`` and ``AnswerGenerator`` flows with optional memory retrieval
that runs **before** knowledge retrieval.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Sequence

from memory.manager import MemoryManager
from memory.models import BuiltMemoryContext

logger = logging.getLogger(__name__)


@dataclass
class MemoryAugmentedResult:
    """Result of a memory-augmented chat turn."""

    answer: str | None = None
    memory_context: BuiltMemoryContext | None = None
    memories_saved: int = 0
    retrieval_ms: float = 0.0
    memory_retrieval_ms: float = 0.0
    knowledge_retrieval_ms: float = 0.0
    extras: dict[str, Any] = field(default_factory=dict)


def enrich_retrieval_query(query: str, memory_context: BuiltMemoryContext) -> str:
    """Enrich the knowledge retrieval query with salient user facts."""
    facts = [m.record.content for m in memory_context.memories[:3]]
    if memory_context.summary.current_goal:
        facts.insert(0, f"goal: {memory_context.summary.current_goal}")
    if not facts:
        return query
    return f"{' '.join(facts)} {query}".strip()


def chat_with_memory(
    pipeline: Any,
    memory_manager: MemoryManager,
    query: str,
    user_id: str,
    *,
    use_generator: bool = False,
    generator: Any | None = None,
) -> MemoryAugmentedResult:
    """Run memory retrieval before the existing RAG pipeline.

    Flow::

        User → Session/Memory Save → Memory Retrieval → Summary/Context
             → Knowledge Retrieval → Generator → Verification → Answer

    Args:
        pipeline: Existing ``RagPipeline`` instance (Phase 4.x).
        memory_manager: Phase 6 memory manager.
        query: User question.
        user_id: Stable user identifier.
        use_generator: When True, use Phase 5 ``AnswerGenerator`` instead of
            ``RagPipeline.chat``.
        generator: Optional pre-built ``AnswerGenerator``.

    Returns:
        :class:`MemoryAugmentedResult` with pipeline output and memory context.
    """
    t0 = time.perf_counter()

    saved = memory_manager.process_user_message(user_id, query)
    memory_context = memory_manager.build_context(query, user_id)
    enriched_query = enrich_retrieval_query(query, memory_context)

    t_mem = time.perf_counter()
    memory_ms = (t_mem - t0) * 1000.0

    if use_generator:
        from src.rag.generator import AnswerGenerator

        gen = generator or AnswerGenerator()
        # Caller is expected to pass retrieved chunks externally in full integration;
        # here we only attach memory context metadata.
        result = MemoryAugmentedResult(
            memory_context=memory_context,
            memories_saved=len(saved),
            memory_retrieval_ms=memory_ms,
            extras={"enriched_query": enriched_query},
        )
        return result

    response = pipeline.chat(enriched_query, update_history=False)
    knowledge_ms = getattr(response, "retrieval_ms", 0.0) or 0.0
    total_ms = (time.perf_counter() - t0) * 1000.0

    sess = memory_manager.session(user_id)
    sess.add_turn("assistant", response.answer)

    return MemoryAugmentedResult(
        answer=response.answer,
        memory_context=memory_context,
        memories_saved=len(saved),
        retrieval_ms=total_ms,
        memory_retrieval_ms=memory_ms,
        knowledge_retrieval_ms=knowledge_ms,
        extras={
            "confidence": getattr(response, "confidence", None),
            "sources": getattr(response, "sources", []),
            "enriched_query": enriched_query,
        },
    )
