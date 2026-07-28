"""Build LLM-ready context from memory, summary, and knowledge."""

from __future__ import annotations

import logging
from typing import Sequence

from .config import load_memory_config
from .models import BuiltMemoryContext, ConversationSummary, MemoryConfig, RankedMemory

logger = logging.getLogger(__name__)


class MemoryContextBuilder:
    """Assemble formatted prompt context for the generation layer."""

    def __init__(self, config: MemoryConfig | None = None) -> None:
        self.config = config or load_memory_config()

    def build(
        self,
        question: str,
        *,
        summary: ConversationSummary | None = None,
        memories: Sequence[RankedMemory] | None = None,
        knowledge_text: str = "",
    ) -> BuiltMemoryContext:
        """Build a composite context block.

        Args:
            question: Current user question.
            summary: Optional conversation summary.
            memories: Ranked relevant memories.
            knowledge_text: Retrieved knowledge base context.

        Returns:
            :class:`BuiltMemoryContext` with rendered ``text``.
        """
        summary = summary or ConversationSummary()
        memories = list(memories or [])
        sections: list[str] = []

        summary_text = summary.render()
        sections.append(summary_text)

        if memories:
            mem_lines = ["## Relevant User Memories", ""]
            for i, mem in enumerate(memories, start=1):
                mem_lines.append(
                    f"{i}. [{mem.record.category}] {mem.record.content} "
                    f"(score={mem.score:.3f})"
                )
            sections.append("\n".join(mem_lines))

        if knowledge_text.strip():
            sections.append("## Retrieved Knowledge\n\n" + knowledge_text.strip())

        sections.append(f"## Current Question\n\n{question.strip()}")

        text = "\n\n".join(sections)
        token_estimate = int(len(text) / self.config.chars_per_token)
        return BuiltMemoryContext(
            summary=summary,
            memories=memories,
            knowledge_text=knowledge_text,
            question=question,
            text=text,
            token_estimate=token_estimate,
        )
