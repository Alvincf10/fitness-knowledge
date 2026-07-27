"""End-to-end build and query orchestration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from .bm25_index import BM25Index
from .chunker import MarkdownChunker, load_chunks_jsonl
from .config import Config, load_config, setup_logging
from .embeddings import EmbeddingGenerator, EmbeddingProvider, create_embedding_provider
from .expansion import expand_query
from .guard import apply_guard
from .hybrid import apply_title_boost, fuse
from .models import Chunk, Citation, RetrievalHit, RetrievalResult
from .reranker import Reranker, create_reranker
from .vectorstore import FaissStore

logger = logging.getLogger(__name__)


class RetrievalPipeline:
    """Build indexes and run hybrid retrieval with citations + guard."""

    def __init__(
        self,
        config: Config | None = None,
        *,
        embedder: EmbeddingProvider | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self.config = config or load_config()
        setup_logging(self.config.log_level)
        self._embedder_override = embedder
        self._reranker_override = reranker
        self.chunks: list[Chunk] = []
        self.chunk_by_id: dict[str, Chunk] = {}
        self.faiss = FaissStore(self.config)
        self.bm25 = BM25Index(self.config)
        self._embed_provider: EmbeddingProvider | None = embedder
        self._reranker: Reranker | None = reranker
        self._ready = False

    def build(self, *, force: bool = False) -> dict:
        """Chunk → embed → FAISS → BM25."""
        chunker = MarkdownChunker(self.config)
        self.chunks = chunker.build(force=force)
        self.chunk_by_id = {c.chunk_id: c for c in self.chunks}

        provider = self._embedder_override or create_embedding_provider(self.config)
        self._embed_provider = provider
        generator = EmbeddingGenerator(self.config, provider)
        matrix = generator.build(self.chunks, force=force)

        self.faiss.build(matrix, [c.chunk_id for c in self.chunks])
        self.bm25.build(self.chunks)
        self._reranker = self._reranker_override or create_reranker(self.config)
        self._ready = True

        return {
            "chunks": len(self.chunks),
            "embedding_dim": int(matrix.shape[1]) if matrix.size else 0,
            "embedding_provider": provider.name,
            "faiss_type": self.config.faiss.index_type,
            "reranker": self._reranker.name,
        }

    def load(self) -> None:
        """Load persisted artifacts for querying without a full rebuild."""
        self.chunks = load_chunks_jsonl(self.config.path("chunks"))
        self.chunk_by_id = {c.chunk_id: c for c in self.chunks}
        self.faiss.load()
        self.bm25.load()
        if self._embed_provider is None:
            self._embed_provider = self._embedder_override or create_embedding_provider(
                self.config
            )
        if self._reranker is None:
            self._reranker = self._reranker_override or create_reranker(self.config)
        self._ready = True
        logger.info("Pipeline ready (%d chunks)", len(self.chunks))

    def _ensure_ready(self) -> None:
        if not self._ready:
            self.load()

    def _hit_from_id(self, chunk_id: str, score: float) -> RetrievalHit | None:
        chunk = self.chunk_by_id.get(chunk_id)
        if chunk is None:
            return None
        citation = Citation(
            file_path=chunk.file_path,
            heading=chunk.heading,
            paragraph=chunk.content,
            source=chunk.source or chunk.file_path,
            url=chunk.url,
        )
        return RetrievalHit(chunk_id=chunk_id, score=score, citation=citation, chunk=chunk)

    def retrieve(self, query: str) -> RetrievalResult:
        """Hybrid retrieve → rerank → guard."""
        self._ensure_ready()
        assert self._embed_provider is not None
        assert self._reranker is not None

        rc = self.config.retrieval
        expanded = expand_query(query)

        qvec = self._embed_provider.embed([query], is_query=True)[0]
        semantic = self.faiss.search(qvec, top_k=rc.top_k_semantic)
        lexical = self.bm25.search(expanded, top_k=rc.top_k_bm25)

        fused = fuse(
            semantic,
            lexical,
            method=rc.fusion,
            rrf_k=rc.rrf_k,
            semantic_weight=rc.semantic_weight,
            bm25_weight=rc.bm25_weight,
            top_n=rc.top_k_fused,
        )

        candidates: list[RetrievalHit] = []
        for cid, score in fused:
            hit = self._hit_from_id(cid, score)
            if hit:
                candidates.append(hit)

        candidates = apply_title_boost(query, candidates)

        # Guard on fusion/title-boost scores (stable scale). Reranker may use
        # a different score range (cross-encoder logits).
        gated = apply_guard(query, candidates, rc, expanded_query=expanded)
        if gated.insufficient_evidence:
            return gated

        reranked = self._reranker.rerank(
            query, candidates, top_k=self.config.reranker.top_k or rc.top_k_final
        )
        return RetrievalResult(
            query=query,
            hits=reranked,
            insufficient_evidence=False,
            message=None,
            expanded_query=expanded,
        )


def build_pipeline(
    config_path: str | Path | None = None,
    knowledge_root: str | Path | None = None,
    *,
    force: bool = False,
) -> dict:
    cfg = load_config(config_path, knowledge_root)
    pipe = RetrievalPipeline(cfg)
    return pipe.build(force=force)
