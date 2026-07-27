"""Cross-encoder reranker for RAG (BGE / Jina / NoOp) with latency logging."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Sequence

from retrieval.models import RetrievalHit
from retrieval.reranker import Reranker, create_reranker

from .config import RagConfig

logger = logging.getLogger(__name__)


@dataclass
class RerankResult:
    hits: list[RetrievalHit]
    elapsed_ms: float
    provider: str
    device: str | None = None


class RagReranker:
    """Timing wrapper around Phase 3 reranker adapters (batch + GPU aware)."""

    def __init__(
        self,
        config: RagConfig,
        *,
        backend: Reranker | None = None,
    ) -> None:
        self.config = config
        if not config.rag.enable_reranker:
            config.retrieval.reranker.provider = "noop"
            config.reranker.provider = "noop"
        elif config.reranker.provider:
            config.retrieval.reranker.provider = config.reranker.provider
        if config.reranker.model:
            config.retrieval.reranker.model = config.reranker.model
        if backend is not None:
            self._backend = backend
        else:
            self._backend = create_reranker(
                config.retrieval,
                batch_size=config.reranker.batch_size,
                device=config.reranker.device,
                fallback_model=config.reranker.fallback_model,
            )

    @property
    def name(self) -> str:
        return self._backend.name

    @property
    def device(self) -> str | None:
        return getattr(self._backend, "device", None)

    def rerank(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
        *,
        top_k: int | None = None,
    ) -> RerankResult:
        k = top_k or self.config.rag.top_k_rerank or self.config.reranker.top_k
        t0 = time.perf_counter()
        out = self._backend.rerank(query, hits, top_k=k)
        elapsed = (time.perf_counter() - t0) * 1000.0
        logger.info(
            "rerank provider=%s device=%s in=%d out=%d latency_ms=%.2f",
            self.name,
            self.device,
            len(hits),
            len(out),
            elapsed,
        )
        return RerankResult(
            hits=out,
            elapsed_ms=elapsed,
            provider=self.name,
            device=self.device,
        )
