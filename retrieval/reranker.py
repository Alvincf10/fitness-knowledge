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


def _resolve_device(device: str = "auto") -> str:
    d = (device or "auto").lower()
    if d == "cpu":
        return "cpu"
    if d in {"cuda", "gpu"}:
        return "cuda"
    # auto
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def _load_cross_encoder(
    model: str,
    *,
    trust_remote_code: bool = False,
    device: str = "auto",
):
    """Load a CrossEncoder with GPU support and CPU fallback."""
    resolved = _resolve_device(device)
    try:
        from sentence_transformers import CrossEncoder

        kwargs: dict = {"device": resolved}
        if trust_remote_code:
            kwargs["trust_remote_code"] = True
        enc = CrossEncoder(model, **kwargs)
        logger.info("Loaded CrossEncoder %s on %s", model, resolved)
        return enc, "st", resolved
    except Exception as st_exc:
        try:
            from FlagEmbedding import FlagReranker

            use_fp16 = resolved == "cuda"
            return FlagReranker(model, use_fp16=use_fp16), "flag", resolved
        except Exception as flag_exc:
            raise RuntimeError(
                f"Failed to load reranker model '{model}'. Install "
                f"sentence-transformers or FlagEmbedding. "
                f"st={st_exc}; flag={flag_exc}"
            ) from st_exc


class BGEReranker(Reranker):
    """BGE cross-encoder reranker with batch inference + device selection."""

    name = "bge"

    def __init__(
        self,
        model: str = "BAAI/bge-reranker-v2-m3",
        *,
        batch_size: int = 16,
        device: str = "auto",
        fallback_model: str | None = "BAAI/bge-reranker-base",
    ) -> None:
        self.batch_size = batch_size
        self.device_pref = device
        try:
            self._model, self._backend, self.device = _load_cross_encoder(
                model, device=device, trust_remote_code="v2-m3" in model
            )
            self.model_name = model
        except Exception as primary_exc:
            if not fallback_model or fallback_model == model:
                raise
            logger.warning(
                "Primary reranker %s failed (%s); falling back to %s",
                model,
                primary_exc,
                fallback_model,
            )
            self._model, self._backend, self.device = _load_cross_encoder(
                fallback_model, device=device
            )
            self.model_name = fallback_model
        logger.info(
            "BGE reranker ready model=%s backend=%s device=%s batch=%d",
            self.model_name,
            self._backend,
            self.device,
            self.batch_size,
        )

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
            scores = self._model.predict(
                pairs,
                batch_size=self.batch_size,
                show_progress_bar=False,
            )
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

    def __init__(
        self,
        model: str = "jinaai/jina-reranker-v2-base-multilingual",
        *,
        batch_size: int = 16,
        device: str = "auto",
    ) -> None:
        self.batch_size = batch_size
        self._model, self._backend, self.device = _load_cross_encoder(
            model, trust_remote_code=True, device=device
        )
        self.model_name = model
        logger.info("Loaded Jina reranker %s on %s", model, self.device)

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
        scores = self._model.predict(
            pairs, batch_size=self.batch_size, show_progress_bar=False
        )
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


def create_reranker(config: Config, *, batch_size: int = 16, device: str = "auto", fallback_model: str | None = None) -> Reranker:
    provider = config.reranker.provider.lower()
    if provider in {"noop", "none", "off"}:
        return NoOpReranker()
    if provider == "bge":
        model = config.reranker.model or "BAAI/bge-reranker-v2-m3"
        try:
            return BGEReranker(
                model=model,
                batch_size=batch_size,
                device=device,
                fallback_model=fallback_model or "BAAI/bge-reranker-base",
            )
        except Exception as exc:
            logger.warning("BGE reranker unavailable (%s); using noop", exc)
            return NoOpReranker()
    if provider == "jina":
        model = config.reranker.model or "jinaai/jina-reranker-v2-base-multilingual"
        try:
            return JinaReranker(model=model, batch_size=batch_size, device=device)
        except Exception as exc:
            logger.warning("Jina reranker unavailable (%s); using noop", exc)
            return NoOpReranker()
    raise ValueError(f"Unknown reranker provider: {provider}")
