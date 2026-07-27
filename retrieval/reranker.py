"""Reranking adapters: NoOp, BGE, and Jina (config-selectable)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Sequence

from .config import Config
from .models import RetrievalHit

logger = logging.getLogger(__name__)


class Reranker(ABC):
    name: str = "base"

    @abstractmethod
    def rerank(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
        *,
        top_k: int = 10,
    ) -> list[RetrievalHit]:
        ...


class NoOpReranker(Reranker):
    """Pass-through: keep hybrid order, truncate to top_k."""

    name = "noop"

    def rerank(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
        *,
        top_k: int = 10,
    ) -> list[RetrievalHit]:
        return list(hits)[:top_k]


def _load_cross_encoder(model: str, *, trust_remote_code: bool = False):
    """Load a CrossEncoder, preferring sentence-transformers then FlagEmbedding."""
    try:
        from sentence_transformers import CrossEncoder

        kwargs = {"trust_remote_code": True} if trust_remote_code else {}
        return CrossEncoder(model, **kwargs), "st"
    except Exception as st_exc:
        try:
            from FlagEmbedding import FlagReranker

            return FlagReranker(model, use_fp16=True), "flag"
        except Exception as flag_exc:
            raise RuntimeError(
                f"Failed to load reranker model '{model}'. Install "
                f"sentence-transformers or FlagEmbedding. "
                f"st={st_exc}; flag={flag_exc}"
            ) from st_exc


class BGEReranker(Reranker):
    """BGE cross-encoder reranker (base/large via config model name)."""

    name = "bge"

    def __init__(self, model: str = "BAAI/bge-reranker-base") -> None:
        self.model_name = model
        self._model, self._backend = _load_cross_encoder(model)
        logger.info("Loaded BGE reranker %s via %s", model, self._backend)

    def rerank(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
        *,
        top_k: int = 10,
    ) -> list[RetrievalHit]:
        if not hits:
            return []
        pairs = [(query, h.citation.paragraph) for h in hits]
        if self._backend == "flag":
            scores = self._model.compute_score(pairs)
            if isinstance(scores, float):
                scores = [scores]
        else:
            scores = self._model.predict(pairs)
        rescored = [
            RetrievalHit(
                chunk_id=h.chunk_id,
                score=float(s),
                citation=h.citation,
                chunk=h.chunk,
            )
            for h, s in zip(hits, scores)
        ]
        rescored.sort(key=lambda x: x.score, reverse=True)
        return rescored[:top_k]


class JinaReranker(Reranker):
    """Jina reranker via sentence-transformers CrossEncoder."""

    name = "jina"

    def __init__(self, model: str = "jinaai/jina-reranker-v2-base-multilingual") -> None:
        self.model_name = model
        self._model, self._backend = _load_cross_encoder(model, trust_remote_code=True)
        logger.info("Loaded Jina reranker %s via %s", model, self._backend)

    def rerank(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
        *,
        top_k: int = 10,
    ) -> list[RetrievalHit]:
        if not hits:
            return []
        pairs = [(query, h.citation.paragraph) for h in hits]
        scores = self._model.predict(pairs)
        rescored = [
            RetrievalHit(
                chunk_id=h.chunk_id,
                score=float(s),
                citation=h.citation,
                chunk=h.chunk,
            )
            for h, s in zip(hits, scores)
        ]
        rescored.sort(key=lambda x: x.score, reverse=True)
        return rescored[:top_k]


def create_reranker(config: Config) -> Reranker:
    provider = config.reranker.provider.lower()
    if provider in {"noop", "none", "off"}:
        return NoOpReranker()
    if provider == "bge":
        model = config.reranker.model or "BAAI/bge-reranker-base"
        return BGEReranker(model=model)
    if provider == "jina":
        model = config.reranker.model or "jinaai/jina-reranker-v2-base-multilingual"
        return JinaReranker(model=model)
    raise ValueError(f"Unknown reranker provider: {provider}")
