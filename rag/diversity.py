"""Source diversity: per-document caps, section + semantic diversity."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Sequence

from retrieval.models import RetrievalHit


def _doc_key(hit: RetrievalHit) -> str:
    chunk = hit.chunk
    if chunk and chunk.doc_id:
        return chunk.doc_id
    if chunk and chunk.file_path:
        return chunk.file_path
    return hit.citation.file_path or hit.chunk_id


def _section_key(hit: RetrievalHit) -> str:
    heading = (hit.citation.heading or "").strip().lower()
    if hit.chunk and hit.chunk.section_path:
        return " > ".join(hit.chunk.section_path).lower()
    return heading or hit.chunk_id


def _token_set(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def diversify_hits(
    hits: Sequence[RetrievalHit],
    *,
    top_k: int,
    max_per_doc: int = 2,
    max_per_section: int = 1,
    semantic_jaccard_max: float = 0.85,
    enabled: bool = True,
) -> list[RetrievalHit]:
    """Select diverse hits while preserving score order as much as possible.

    - Cap chunks per document (default 2)
    - Prefer different sections within a document
    - Skip near-duplicate paragraphs (high Jaccard)
    """
    if not enabled:
        return list(hits)[:top_k]
    if not hits or top_k <= 0:
        return []

    selected: list[RetrievalHit] = []
    per_doc: dict[str, int] = defaultdict(int)
    per_section: dict[str, int] = defaultdict(int)
    selected_tokens: list[set[str]] = []

    for hit in hits:
        if len(selected) >= top_k:
            break
        doc = _doc_key(hit)
        sec = f"{doc}::{_section_key(hit)}"
        if per_doc[doc] >= max_per_doc:
            continue
        if per_section[sec] >= max_per_section and max_per_section > 0:
            # Allow second chunk from same section only if we still need diversity fill
            # and document cap not reached — skip for strict section diversity
            continue

        toks = _token_set(hit.citation.paragraph)
        if any(_jaccard(toks, prev) >= semantic_jaccard_max for prev in selected_tokens):
            continue

        selected.append(hit)
        per_doc[doc] += 1
        per_section[sec] += 1
        selected_tokens.append(toks)

    # If too aggressive, fill remaining slots relaxing section/semantic constraints
    if len(selected) < top_k:
        selected_ids = {h.chunk_id for h in selected}
        for hit in hits:
            if len(selected) >= top_k:
                break
            if hit.chunk_id in selected_ids:
                continue
            doc = _doc_key(hit)
            if per_doc[doc] >= max_per_doc:
                continue
            selected.append(hit)
            selected_ids.add(hit.chunk_id)
            per_doc[doc] += 1

    return selected
