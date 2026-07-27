"""Data models for the RAG chat pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SourceRef:
    """Structured citation for API / UI consumers."""

    index: int
    chunk_id: str
    title: str | None
    heading: str
    file_path: str
    section: str | None = None
    file: str | None = None
    category: str | None = None
    subcategory: str | None = None
    slug: str | None = None
    source: str | None = None
    url: str | None = None
    score: float = 0.0
    confidence: float = 0.0
    snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Prefer compact citation shape alongside full fields
        d["file"] = self.file or self.file_path
        d["section"] = self.section or self.heading
        return d


@dataclass
class PromptBundle:
    """Messages ready for an LLM chat completion call."""

    system: str
    user: str
    context_block: str
    source_ids: list[str] = field(default_factory=list)
    language: str = "en"

    def to_messages(self) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system},
            {"role": "user", "content": self.user},
        ]


@dataclass
class ChatResponse:
    """Formatted RAG response with timings and confidence."""

    answer: str
    sources: list[SourceRef] = field(default_factory=list)
    confidence: float = 0.0
    retrieval_ms: float = 0.0
    rerank_ms: float = 0.0
    embedding_ms: float = 0.0
    llm_ms: float = 0.0
    total_ms: float = 0.0
    insufficient_knowledge: bool = False
    abstain_reason: str | None = None
    query: str = ""
    normalized_query: str = ""
    model: str | None = None
    language: str = "en"
    citations: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "language": self.language,
            "confidence": self.confidence,
            "sources": [s.to_dict() for s in self.sources],
            "citations": self.citations
            or [
                {
                    "title": s.title or s.heading,
                    "file": s.file or s.file_path,
                    "section": s.section or s.heading,
                    "confidence": round(s.confidence, 4),
                }
                for s in self.sources
            ],
            "retrieval_ms": round(self.retrieval_ms, 3),
            "rerank_ms": round(self.rerank_ms, 3),
            "embedding_ms": round(self.embedding_ms, 3),
            "llm_ms": round(self.llm_ms, 3),
            "total_ms": round(self.total_ms, 3),
            "insufficient_knowledge": self.insufficient_knowledge,
            "abstain_reason": self.abstain_reason,
            "query": self.query,
            "normalized_query": self.normalized_query,
            "model": self.model,
        }
