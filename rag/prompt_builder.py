"""Hallucination-resistant prompt assembly from retrieved context only."""

from __future__ import annotations

from typing import Sequence

from retrieval.models import RetrievalHit

from .citations import sources_from_hits
from .config import RagConfig
from .language import LANGUAGE_NAMES, LanguageInfo
from .models import PromptBundle, SourceRef

DEFAULT_SYSTEM = """You are a fitness knowledge assistant grounded ONLY in the provided knowledge-base context.

The user may ask questions in any language.
The retrieved knowledge is written in English.
Reason over the English context.
Respond in the same language as the user's question.

Strict rules:
1. Answer ONLY using information present in the CONTEXT section below.
2. If the context is insufficient, say you do not have enough evidence in the knowledge base — in the user's language. Do not invent facts, dosages, or medical advice.
3. Cite sources inline using bracket markers like [1], [2] that match the context blocks.
4. Never translate citation file paths, slugs, or source identifiers. Keep them exactly as given (e.g. exercises/chest/barbell-bench-press.md).
5. Keep common exercise names in English (Bench Press, Romanian Deadlift, Pull-Up, Lat Pulldown, etc.) even when answering in another language.
6. Keep technical terms accurate; do not invent Indonesian or other-language medical claims beyond the English evidence.
7. Prefer precise, evidence-oriented language. Do not diagnose medical conditions.
8. Never claim knowledge outside the provided context.
"""


def _format_context_blocks(sources: Sequence[SourceRef], hits: Sequence[RetrievalHit]) -> str:
    blocks: list[str] = []
    for src, hit in zip(sources, hits):
        title = src.title or src.heading
        # Paths stay English / unchanged — never localize
        header = f"[{src.index}] {title} | {src.file_path} | {src.heading}"
        body = hit.citation.paragraph.strip()
        blocks.append(f"{header}\n{body}")
    return "\n\n---\n\n".join(blocks)


def build_prompt(
    query: str,
    hits: Sequence[RetrievalHit],
    *,
    config: RagConfig | None = None,
    system_override: str | None = None,
    language: LanguageInfo | str | None = None,
) -> PromptBundle:
    """Assemble a grounded chat prompt with numbered context citations."""
    sources = sources_from_hits(hits)
    context = _format_context_blocks(sources, hits) if hits else "(no context)"
    system = (
        system_override
        or (config.llm.system_prompt if config and config.llm.system_prompt else None)
        or DEFAULT_SYSTEM
    )

    if isinstance(language, LanguageInfo):
        lang_code = language.code
        lang_name = language.name
    elif isinstance(language, str) and language:
        lang_code = language.lower()
        lang_name = LANGUAGE_NAMES.get(lang_code, language)
    else:
        lang_code = "en"
        lang_name = "English"

    user = (
        f"USER_LANGUAGE: {lang_code} ({lang_name})\n\n"
        f"CONTEXT (English knowledge base — do not translate file paths):\n{context}\n\n"
        f"QUESTION:\n{query.strip()}\n\n"
        f"Answer the question in {lang_name} using only the CONTEXT. "
        "Include citation markers [n]. Keep exercise names and source paths in English. "
        "If context is insufficient, say so clearly in the user's language."
    )
    return PromptBundle(
        system=system,
        user=user,
        context_block=context,
        source_ids=[h.chunk_id for h in hits],
        language=lang_code,
    )
