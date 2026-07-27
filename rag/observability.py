"""Structured JSON observability for the RAG pipeline."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

logger = logging.getLogger("rag.observability")


@dataclass
class RagTrace:
    """One request's timing + ranking trace (JSON-serializable)."""

    query: str
    normalized_query: str = ""
    language: str = "en"
    confidence: float = 0.0
    abstained: bool = False
    abstain_reason: str | None = None
    embedding_ms: float = 0.0
    retrieval_ms: float = 0.0
    rerank_ms: float = 0.0
    llm_ms: float = 0.0
    total_ms: float = 0.0
    prompt_chars: int = 0
    retrieved_ids: list[str] = field(default_factory=list)
    reranked_ids: list[str] = field(default_factory=list)
    final_ids: list[str] = field(default_factory=list)
    top_k_retrieve: int = 0
    top_k_final: int = 0
    reranker: str = "noop"
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def log_trace(trace: RagTrace, *, structured: bool = True) -> None:
    """Emit a single structured log line for the request."""
    payload = trace.to_dict()
    if structured:
        logger.info("rag_trace %s", json.dumps(payload, ensure_ascii=False, default=str))
    else:
        logger.info(
            "query=%r lang=%s conf=%.3f abstain=%s ret=%.1fms rerank=%.1fms total=%.1fms",
            trace.query,
            trace.language,
            trace.confidence,
            trace.abstained,
            trace.retrieval_ms,
            trace.rerank_ms,
            trace.total_ms,
        )


def ids_from_hits(hits: Sequence[Any]) -> list[str]:
    out: list[str] = []
    for h in hits:
        cid = getattr(h, "chunk_id", None)
        if cid:
            out.append(str(cid))
    return out
