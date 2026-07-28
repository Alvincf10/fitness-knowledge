"""Semantic memory retrieval with metadata filtering."""

from __future__ import annotations

import logging
import time
from typing import Sequence

from retrieval.embeddings import EmbeddingProvider, HashProvider

from .config import load_memory_config
from .extractor import MemoryExtractor
from .models import MemoryConfig, RankedMemory
from .ranker import MemoryRanker
from .storage import MemoryStorage

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """Retrieve relevant long-term memories for a query."""

    def __init__(
        self,
        storage: MemoryStorage,
        embedder: EmbeddingProvider | None = None,
        *,
        config: MemoryConfig | None = None,
        extractor: MemoryExtractor | None = None,
        ranker: MemoryRanker | None = None,
    ) -> None:
        self.config = config or load_memory_config()
        self.storage = storage
        self.embedder = embedder or HashProvider(dim=self.config.embedding_dim)
        self.extractor = extractor or MemoryExtractor()
        self.ranker = ranker or MemoryRanker(self.config)

    def retrieve(
        self,
        user_id: str,
        query: str,
        *,
        top_k: int | None = None,
        categories: Sequence[str] | None = None,
    ) -> tuple[list[RankedMemory], float]:
        """Retrieve ranked memories for a user query.

        Args:
            user_id: User identifier.
            query: Natural language question or statement.
            top_k: Maximum memories to return.
            categories: Optional category filter; inferred from query when omitted.

        Returns:
            Tuple of (ranked memories, elapsed_ms).
        """
        t0 = time.perf_counter()
        k = top_k or self.config.top_k
        inferred = list(categories) if categories else self.extractor.infer_categories_from_query(query)

        records = self.storage.get_by_user(user_id)
        if inferred:
            filtered = [r for r in records if r.category in inferred]
            if filtered:
                records = filtered

        if not records:
            return [], (time.perf_counter() - t0) * 1000.0

        query_vec = self.embedder.embed([query], is_query=True)[0]
        candidates: list[tuple] = []
        for record in records:
            if not record.embedding:
                continue
            sim = self.storage.cosine_similarity(query_vec, record.embedding)
            candidates.append((record, sim))

        ranked = self.ranker.rank(candidates)[:k]
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        logger.debug(
            "Retrieved %d/%d memories for user=%s in %.2fms",
            len(ranked),
            len(records),
            user_id,
            elapsed_ms,
        )
        return ranked, elapsed_ms
