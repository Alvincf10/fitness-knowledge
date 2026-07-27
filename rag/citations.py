"""Structured citation / source reference builders."""

from __future__ import annotations

from typing import Any, Sequence

from retrieval.models import RetrievalHit

from .models import SourceRef
from .retriever import confidence_from_hits

_SNIPPET_LEN = 280


def _snippet(text: str, limit: int = _SNIPPET_LEN) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def _hit_confidence(hit: RetrievalHit, *, rank_confidence: float | None = None) -> float:
    """Per-citation confidence from score, optionally blended with rank confidence."""
    local = confidence_from_hits([hit])
    if rank_confidence is None:
        return local
    return max(0.0, min(1.0, 0.5 * local + 0.5 * rank_confidence))


def sources_from_hits(
    hits: Sequence[RetrievalHit],
    *,
    rank_confidence: float | None = None,
) -> list[SourceRef]:
    """Convert ranked retrieval hits into structured source references.

    Sorted by relevance (input order assumed ranked). Includes section + confidence.
    """
    sources: list[SourceRef] = []
    for i, hit in enumerate(hits, start=1):
        chunk = hit.chunk
        citation = hit.citation
        section = citation.heading
        if chunk and chunk.section_path:
            section = " > ".join(chunk.section_path)
        sources.append(
            SourceRef(
                index=i,
                chunk_id=hit.chunk_id,
                title=(chunk.title if chunk else None),
                heading=citation.heading,
                section=section,
                file_path=citation.file_path,
                file=citation.file_path,
                category=(chunk.category if chunk else None),
                subcategory=(chunk.subcategory if chunk else None),
                slug=(chunk.slug if chunk else None),
                source=citation.source,
                url=citation.url,
                score=float(hit.score),
                confidence=_hit_confidence(hit, rank_confidence=rank_confidence),
                snippet=_snippet(citation.paragraph),
            )
        )
    return sources


def citations_compact(sources: Sequence[SourceRef]) -> list[dict[str, Any]]:
    """API-friendly citation objects: title, file, section, confidence."""
    return [
        {
            "title": s.title or s.heading,
            "file": s.file or s.file_path,
            "section": s.section or s.heading,
            "confidence": round(float(s.confidence), 4),
        }
        for s in sources
    ]


def format_sources_markdown(sources: Sequence[SourceRef]) -> str:
    """Human-readable source list for CLI / logs."""
    lines: list[str] = []
    for s in sources:
        title = s.title or s.heading
        sec = s.section or s.heading
        lines.append(
            f"[{s.index}] {title} — `{s.file_path}` §{sec} "
            f"(score={s.score:.4f}, conf={s.confidence:.3f})"
        )
        if s.snippet:
            lines.append(f"    {s.snippet}")
    return "\n".join(lines)


def citation_markers(sources: Sequence[SourceRef]) -> str:
    """Inline marker legend for prompts (e.g. [1], [2])."""
    return ", ".join(f"[{s.index}]={s.file_path}" for s in sources)
