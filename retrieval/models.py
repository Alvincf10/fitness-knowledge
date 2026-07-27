"""Core data models for the retrieval pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Chunk:
    """A single indexed text segment from a Markdown document."""

    chunk_id: str
    content: str
    file_path: str
    heading: str
    category: str | None = None
    subcategory: str | None = None
    slug: str | None = None
    title: str | None = None
    muscle: list[str] = field(default_factory=list)
    equipment: list[str] = field(default_factory=list)
    difficulty: str | None = None
    source: str | None = None
    last_updated: str | None = None
    url: str | None = None
    doc_id: str | None = None
    token_estimate: int = 0
    section_path: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Chunk:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Citation:
    """Provenance for a retrieved chunk."""

    file_path: str
    heading: str
    paragraph: str
    source: str
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalHit:
    """A ranked retrieval candidate with score and citation."""

    chunk_id: str
    score: float
    citation: Citation
    chunk: Chunk | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "score": self.score,
            "citation": self.citation.to_dict(),
            "chunk": self.chunk.to_dict() if self.chunk else None,
        }


@dataclass
class RetrievalResult:
    """Final query response, possibly blocked by the hallucination guard."""

    query: str
    hits: list[RetrievalHit] = field(default_factory=list)
    insufficient_evidence: bool = False
    message: str | None = None
    expanded_query: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "hits": [h.to_dict() for h in self.hits],
            "insufficient_evidence": self.insufficient_evidence,
            "message": self.message,
            "expanded_query": self.expanded_query,
        }
