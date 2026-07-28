"""Integration helpers for Phase 6 memory + existing RAG stack."""

from __future__ import annotations

from .pipeline_with_memory import MemoryAugmentedResult, chat_with_memory, enrich_retrieval_query

__all__ = ["MemoryAugmentedResult", "chat_with_memory", "enrich_retrieval_query"]
