"""End-to-end RAG orchestration (Phase 4.5 production hardening)."""

from __future__ import annotations

import logging
import time
from typing import Sequence

from retrieval.embeddings import EmbeddingProvider
from retrieval.models import RetrievalHit
from retrieval.reranker import Reranker

from .citations import citations_compact, sources_from_hits
from .config import RagConfig, load_rag_config, setup_logging
from .context import ConversationState, Turn, enrich_query_with_history
from .diversity import diversify_hits
from .dynamic_topk import select_dynamic_topk
from .language import LanguageInfo, detect_language, insufficient_message
from .llm import LLMClient, create_llm, timed_generate
from .models import ChatResponse
from .normalize import load_aliases, normalize_query
from .observability import RagTrace, ids_from_hits, log_trace
from .prompt_builder import build_prompt
from .reranker import RagReranker
from .retriever import Retriever, confidence_from_hits

logger = logging.getLogger(__name__)


class RagPipeline:
    """Production RAG pipeline with confidence gating and citation integrity."""

    def __init__(
        self,
        config: RagConfig | None = None,
        *,
        retriever: Retriever | None = None,
        reranker: RagReranker | None = None,
        llm: LLMClient | None = None,
        embedder: EmbeddingProvider | None = None,
        reranker_backend: Reranker | None = None,
    ) -> None:
        self.config = config or load_rag_config()
        setup_logging(self.config.log_level)
        self.retriever = retriever or Retriever(self.config, embedder=embedder)
        self.reranker = reranker or RagReranker(self.config, backend=reranker_backend)
        self.llm = llm or create_llm(self.config)
        self.aliases = load_aliases(self.config.aliases_path)
        self.conversation = ConversationState(max_history=self.config.rag.max_history)
        self._ready = False

    def load(self) -> None:
        self.retriever.load()
        self._ready = True
        logger.info(
            "RAG pipeline ready (llm=%s, reranker=%s, mode=%s, features=norm:%s dyn:%s div:%s ctx:%s)",
            self.llm.name,
            self.reranker.name,
            self.config.rag.retrieval_mode,
            self.config.rag.enable_query_normalization,
            self.config.rag.enable_dynamic_topk,
            self.config.rag.enable_source_diversity,
            self.config.rag.enable_conversation_context,
        )

    def _ensure_ready(self) -> None:
        if not self._ready:
            self.load()

    def reset_conversation(self) -> None:
        self.conversation.clear()

    def chat(
        self,
        query: str,
        *,
        history: Sequence[Turn] | ConversationState | None = None,
        update_history: bool = True,
    ) -> ChatResponse:
        """Run the full RAG loop for a user question."""
        self._ensure_ready()
        t_total = time.perf_counter()
        rag = self.config.rag
        original = (query or "").strip()

        if rag.enable_language_detection:
            lang = detect_language(original)
        else:
            lang = LanguageInfo(code="en", name="English", confidence=1.0)

        msg = insufficient_message(
            lang.code,
            fallback=rag.insufficient_knowledge_message,
        )

        norm = normalize_query(
            original,
            aliases=self.aliases,
            enabled=rag.enable_query_normalization,
        )
        q_norm = norm.normalized

        hist = history if history is not None else self.conversation
        retrieval_query = enrich_query_with_history(
            q_norm,
            hist,
            max_history=rag.max_history,
            enabled=rag.enable_conversation_context,
        )

        def _abstain(reason: str, conf: float, retrieval_ms: float = 0.0, emb_ms: float = 0.0) -> ChatResponse:
            total = (time.perf_counter() - t_total) * 1000.0
            trace = RagTrace(
                query=original,
                normalized_query=q_norm,
                language=lang.code,
                confidence=conf,
                abstained=True,
                abstain_reason=reason,
                embedding_ms=emb_ms,
                retrieval_ms=retrieval_ms,
                total_ms=total,
                reranker=self.reranker.name,
            )
            if rag.structured_logging:
                log_trace(trace, structured=True)
            return ChatResponse(
                answer=msg,
                sources=[],
                citations=[],
                confidence=conf,
                retrieval_ms=retrieval_ms,
                embedding_ms=emb_ms,
                rerank_ms=0.0,
                llm_ms=0.0,
                total_ms=total,
                insufficient_knowledge=True,
                abstain_reason=reason,
                query=original,
                normalized_query=q_norm,
                model=self.llm.name,
                language=lang.code,
            )

        if not original:
            return _abstain("empty_query", 0.0)

        retrieved = self.retriever.retrieve(
            retrieval_query,
            language=lang.code,
            top_k=rag.top_k_retrieve,
            grounding_query=q_norm,
        )
        retrieval_ms = retrieved.elapsed_ms
        embedding_ms = retrieved.embedding_ms

        if retrieved.insufficient:
            return _abstain(
                retrieved.abstain_reason or "insufficient_evidence",
                retrieved.confidence,
                retrieval_ms=retrieval_ms,
                emb_ms=embedding_ms,
            )

        # Rerank over candidate pool (typically Top-20 → Top-5)
        if rag.enable_reranker and self.reranker.name != "noop":
            reranked = self.reranker.rerank(
                retrieval_query,
                retrieved.hits,
                top_k=max(rag.top_k_rerank, rag.max_top_k),
            )
        else:
            # Still truncate via noop path for consistent timing API
            reranked = self.reranker.rerank(
                retrieval_query,
                retrieved.hits,
                top_k=max(rag.top_k_rerank, rag.max_top_k),
            )
        hits: list[RetrievalHit] = list(reranked.hits)
        confidence = confidence_from_hits(hits) if hits else retrieved.confidence
        # Prefer pre-rerank confidence for fusion-scale gating when noop
        if self.reranker.name == "noop":
            confidence = max(confidence, retrieved.confidence)

        final_k = select_dynamic_topk(
            confidence,
            bands=rag.dynamic_topk,
            min_k=rag.min_top_k,
            max_k=rag.max_top_k,
            enabled=rag.enable_dynamic_topk,
            default_k=rag.top_k_rerank,
        )

        hits = diversify_hits(
            hits,
            top_k=final_k,
            max_per_doc=rag.max_chunks_per_doc,
            max_per_section=rag.max_chunks_per_section,
            semantic_jaccard_max=rag.semantic_jaccard_max,
            enabled=rag.enable_source_diversity,
        )

        if not hits:
            return _abstain(
                "empty_after_diversity",
                confidence,
                retrieval_ms=retrieval_ms,
                emb_ms=embedding_ms,
            )

        prompt = build_prompt(original, hits, config=self.config, language=lang)
        answer, llm_ms = timed_generate(self.llm, prompt, hits=hits)
        sources = sources_from_hits(hits, rank_confidence=confidence)
        compact = citations_compact(sources)
        total_ms = (time.perf_counter() - t_total) * 1000.0

        if update_history and rag.enable_conversation_context:
            self.conversation.max_history = rag.max_history
            self.conversation.add("user", original)
            self.conversation.add("assistant", answer)

        trace = RagTrace(
            query=original,
            normalized_query=q_norm,
            language=lang.code,
            confidence=confidence,
            abstained=False,
            embedding_ms=embedding_ms,
            retrieval_ms=retrieval_ms,
            rerank_ms=reranked.elapsed_ms,
            llm_ms=llm_ms,
            total_ms=total_ms,
            prompt_chars=len(prompt.system) + len(prompt.user),
            retrieved_ids=ids_from_hits(retrieved.hits),
            reranked_ids=ids_from_hits(reranked.hits),
            final_ids=ids_from_hits(hits),
            top_k_retrieve=rag.top_k_retrieve,
            top_k_final=final_k,
            reranker=self.reranker.name,
            extras={"aliases": norm.aliases_applied, "retrieval_query": retrieval_query[:240]},
        )
        if rag.structured_logging:
            log_trace(trace, structured=True)

        return ChatResponse(
            answer=answer,
            sources=sources,
            citations=compact,
            confidence=confidence,
            retrieval_ms=retrieval_ms,
            embedding_ms=embedding_ms,
            rerank_ms=reranked.elapsed_ms,
            llm_ms=llm_ms,
            total_ms=total_ms,
            insufficient_knowledge=False,
            query=original,
            normalized_query=q_norm,
            model=getattr(self.llm, "model", None) or self.llm.name,
            language=lang.code,
        )


def build_default_pipeline(
    config_path: str | None = None,
    knowledge_root: str | None = None,
) -> RagPipeline:
    cfg = load_rag_config(config_path, knowledge_root)
    pipe = RagPipeline(cfg)
    pipe.load()
    return pipe
