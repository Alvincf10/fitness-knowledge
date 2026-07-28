"""Memory manager — orchestrates extraction, storage, retrieval, and context."""

from __future__ import annotations

import logging
from typing import Sequence

from retrieval.embeddings import EmbeddingProvider, HashProvider, create_embedding_provider
from retrieval.config import load_config as load_retrieval_config

from conversation.session import ConversationSession

from .config import load_memory_config
from .context_builder import MemoryContextBuilder
from .extractor import MemoryExtractor
from .models import (
    BuiltMemoryContext,
    ConversationSummary,
    ExtractedMemory,
    MemoryConfig,
    MemoryRecord,
    RankedMemory,
)
from .ranker import MemoryRanker
from .retriever import MemoryRetriever
from .storage import MemoryStorage
from .summarizer import ConversationSummarizer

logger = logging.getLogger(__name__)


class MemoryManager:
    """High-level API for conversation memory and user context."""

    def __init__(
        self,
        config: MemoryConfig | None = None,
        *,
        storage: MemoryStorage | None = None,
        embedder: EmbeddingProvider | None = None,
        extractor: MemoryExtractor | None = None,
        retriever: MemoryRetriever | None = None,
        ranker: MemoryRanker | None = None,
        summarizer: ConversationSummarizer | None = None,
        context_builder: MemoryContextBuilder | None = None,
    ) -> None:
        self.config = config or load_memory_config()
        self.storage = storage or MemoryStorage(self.config.db_path)
        self.embedder = embedder or self._create_embedder()
        self.extractor = extractor or MemoryExtractor()
        self.ranker = ranker or MemoryRanker(self.config)
        self.retriever = retriever or MemoryRetriever(
            self.storage,
            self.embedder,
            config=self.config,
            extractor=self.extractor,
            ranker=self.ranker,
        )
        self.summarizer = summarizer or ConversationSummarizer()
        self.context_builder = context_builder or MemoryContextBuilder(self.config)
        self._sessions: dict[str, ConversationSession] = {}

    def _create_embedder(self) -> EmbeddingProvider:
        """Use the same embedding stack as the knowledge base when possible."""
        if self.config.embedding_provider == "hash":
            return HashProvider(dim=self.config.embedding_dim)
        try:
            rcfg = load_retrieval_config()
            rcfg.embedding.provider = self.config.embedding_provider
            rcfg.embedding.model = self.config.embedding_model
            return create_embedding_provider(rcfg)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falling back to hash embeddings: %s", exc)
            return HashProvider(dim=self.config.embedding_dim)

    def session(self, user_id: str) -> ConversationSession:
        """Get or create a conversation session for a user."""
        if user_id not in self._sessions:
            self._sessions[user_id] = ConversationSession(user_id=user_id)
        return self._sessions[user_id]

    def extract_memory(self, message: str) -> list[ExtractedMemory]:
        """Extract memories from a user message."""
        return self.extractor.extract(message)

    def save_memory(
        self,
        user_id: str,
        message: str,
        *,
        session: ConversationSession | None = None,
    ) -> list[MemoryRecord]:
        """Extract and persist memories from a user message.

        Session-only facts are stored in short-term session memory; durable
        facts are written to SQLite with embeddings.
        """
        extracted = self.extract_memory(message)
        sess = session or self.session(user_id)
        saved: list[MemoryRecord] = []

        for item in extracted:
            if item.metadata.get("session_only") or item.category == "session":
                key, _, value = item.value.partition("=")
                sess.set_fact(key or item.category, value or item.value)
                continue
            vec = self.embedder.embed([item.content], is_query=False)[0]
            saved.append(self.storage.save(user_id, item, vec))

        sess.add_turn("user", message)
        return saved

    def retrieve_memory(
        self,
        user_id: str,
        query: str,
        *,
        top_k: int | None = None,
        categories: Sequence[str] | None = None,
    ) -> tuple[list[RankedMemory], float]:
        """Retrieve ranked relevant memories."""
        return self.retriever.retrieve(
            user_id,
            query,
            top_k=top_k,
            categories=categories,
        )

    def summarize(
        self,
        user_id: str,
        *,
        session: ConversationSession | None = None,
    ) -> ConversationSummary:
        """Summarize conversation and stored memories for a user."""
        sess = session or self.session(user_id)
        memories = self.storage.get_by_user(user_id)
        return self.summarizer.summarize(
            sess.turns,
            memories,
            session_facts=sess.facts,
        )

    def build_context(
        self,
        question: str,
        user_id: str,
        *,
        knowledge_text: str = "",
        session: ConversationSession | None = None,
    ) -> BuiltMemoryContext:
        """Build full prompt context for the LLM."""
        sess = session or self.session(user_id)
        summary = self.summarize(user_id, session=sess)
        memories, _ = self.retrieve_memory(user_id, question)
        return self.context_builder.build(
            question,
            summary=summary,
            memories=memories,
            knowledge_text=knowledge_text,
        )

    def process_user_message(
        self,
        user_id: str,
        message: str,
    ) -> list[MemoryRecord]:
        """Convenience: save memories from an incoming user turn."""
        return self.save_memory(user_id, message)

    def seed_memories(
        self,
        user_id: str,
        items: Sequence[dict[str, str]],
    ) -> list[MemoryRecord]:
        """Seed memories for evaluation/benchmarks."""
        saved: list[MemoryRecord] = []
        for item in items:
            extracted = ExtractedMemory(
                category=item["category"],
                value=item.get("value", item.get("content", "")),
                content=item.get("content", f"{item['category']}: {item.get('value', '')}"),
                importance=float(item.get("importance", self.config.default_importance)),
            )
            vec = self.embedder.embed([extracted.content], is_query=False)[0]
            saved.append(self.storage.save(user_id, extracted, vec))
        return saved

    def reset_user(self, user_id: str) -> None:
        """Clear long-term and session state for a user."""
        self.storage.delete_user(user_id)
        self._sessions.pop(user_id, None)
