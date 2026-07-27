"""LLM backends for RAG generation (extractive / OpenAI / mock)."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Sequence

from retrieval.models import RetrievalHit

from .citations import sources_from_hits
from .config import LLMConfig, RagConfig
from .models import PromptBundle

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, prompt: PromptBundle, *, hits: Sequence[RetrievalHit] | None = None) -> str:
        ...


class MockLLM(LLMClient):
    """Deterministic stub for unit tests."""

    name = "mock"

    def __init__(self, fixed: str = "Mock answer based on context. [1]") -> None:
        self.fixed = fixed

    def generate(self, prompt: PromptBundle, *, hits: Sequence[RetrievalHit] | None = None) -> str:
        return self.fixed


class ExtractiveLLM(LLMClient):
    """Compose an answer from top retrieved snippets without an external LLM.

    Useful offline / CPU-only deployments and CI. Still citation-aware.
    Localizes the framing text to the user language; KB snippets stay English
    (no translation layer). Full natural answers in Indonesian need provider=openai.
    """

    name = "extractive"

    def __init__(self, *, max_chars: int = 1200) -> None:
        self.max_chars = max_chars

    def generate(self, prompt: PromptBundle, *, hits: Sequence[RetrievalHit] | None = None) -> str:
        lang = (prompt.language or "en").lower()
        if not hits:
            from .language import insufficient_message

            return insufficient_message(lang)
        sources = sources_from_hits(hits)
        parts: list[str] = []
        used = 0
        for src, hit in zip(sources, hits):
            title = src.title or src.heading
            para = " ".join(hit.citation.paragraph.split())
            if "\n\n" in hit.citation.paragraph:
                para = " ".join(hit.citation.paragraph.split("\n\n", 1)[-1].split())
            piece = f"[{src.index}] {title}: {para}"
            if used + len(piece) > self.max_chars and parts:
                break
            parts.append(piece)
            used += len(piece)
        if lang == "id":
            intro = (
                "Berdasarkan knowledge base kebugaran (kutipan sumber tetap dalam "
                "bahasa Inggris; nama latihan tidak diterjemahkan):\n\n"
            )
        else:
            intro = "Based on the fitness knowledge base (citations in brackets):\n\n"
        return intro + "\n\n".join(parts)


class OpenAILLM(LLMClient):
    """OpenAI Chat Completions (or compatible base_url)."""

    name = "openai"

    def __init__(self, cfg: LLMConfig) -> None:
        self.cfg = cfg
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("openai package required for provider=openai") from exc
        kwargs = {}
        if cfg.api_key:
            kwargs["api_key"] = cfg.api_key
        if cfg.base_url:
            kwargs["base_url"] = cfg.base_url
        self._client = OpenAI(**kwargs)
        self.model = cfg.model

    def generate(self, prompt: PromptBundle, *, hits: Sequence[RetrievalHit] | None = None) -> str:
        resp = self._client.chat.completions.create(
            model=self.cfg.model,
            temperature=self.cfg.temperature,
            max_tokens=self.cfg.max_tokens,
            messages=prompt.to_messages(),
        )
        content = resp.choices[0].message.content or ""
        return content.strip()


def create_llm(config: RagConfig) -> LLMClient:
    provider = (config.llm.provider or "extractive").lower()
    if provider in {"extractive", "context", "offline"}:
        return ExtractiveLLM()
    if provider == "mock":
        return MockLLM()
    if provider in {"openai", "chat"}:
        return OpenAILLM(config.llm)
    raise ValueError(f"Unknown LLM provider: {provider}")


def timed_generate(
    client: LLMClient,
    prompt: PromptBundle,
    *,
    hits: Sequence[RetrievalHit] | None = None,
) -> tuple[str, float]:
    t0 = time.perf_counter()
    text = client.generate(prompt, hits=hits)
    return text, (time.perf_counter() - t0) * 1000.0
