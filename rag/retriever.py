"""Dense / hybrid retriever over the existing FAISS HNSW index + metadata."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Literal, Sequence

from retrieval.bm25_index import BM25Index
from retrieval.chunker import load_chunks_jsonl
from retrieval.embeddings import EmbeddingProvider, create_embedding_provider
from retrieval.expansion import expand_query
from retrieval.hybrid import apply_title_boost, fuse
from retrieval.models import Chunk, Citation, RetrievalHit
from retrieval.vectorstore import FaissStore

from .config import RagConfig

logger = logging.getLogger(__name__)

DedupeKey = Literal["doc_id", "file_path", "chunk_id", "none"]

# Generic fitness / question words — ignored for grounding checks so that
# nonsense nouns (unicorn, martian, …) drive abstention decisions.
_GENERIC_TOKENS = {
    "a", "an", "the", "is", "are", "do", "does", "did", "how", "what", "why",
    "when", "where", "which", "who", "i", "me", "my", "for", "to", "of", "in",
    "on", "and", "or", "with", "this", "that", "it", "be", "should", "can",
    "will", "much", "many", "need", "good", "best", "correctly", "answer",
    "fitness", "question", "about", "know", "say", "says", "according",
    "knowledge", "base", "corpus", "article", "articles", "cite", "evidence",
    "training", "exercise", "exercises", "workout", "workouts", "program",
    "programming", "protocol", "protocols", "optimal", "recommended", "dose",
    "dosage", "take", "taking", "use", "using", "beginner", "beginners",
    "intermediate", "advanced", "weekly", "daily", "sets", "reps", "rep",
    "muscle", "muscles", "strength", "hypertrophy", "endurance", "cardio",
    "recovery", "volume", "intensity", "frequency", "progressive", "overload",
    "guide", "guidelines", "practical", "supported", "acsm", "issn", "nsca",
    "from", "our", "your", "their", "them", "than", "then", "also", "just",
    "more", "most", "some", "any", "all", "into", "over", "under", "after",
    "before", "between", "through", "during", "without", "within", "across",
    "include", "includes", "including", "citations", "citation", "specific",
    "specifically", "please", "thanks", "help", "tell", "explain", "define",
    "based", "like", "make", "made", "get", "got", "have", "has", "had",
    "being", "been", "were", "was", "not", "only", "very", "really", "truly",
    "always", "never", "often", "usually", "generally", "typically", "common",
    "mistakes", "mistake", "perform", "performing", "technique", "form",
    "work", "works", "working", "build", "building", "gain", "gains", "loss",
    "fat", "lean", "mass", "body", "bodies", "people", "person", "trainee",
    "trainees", "athlete", "athletes", "coach", "coaching", "sessions",
    "session", "guideline", "position", "stand", "fda", "approved",
}


@dataclass
class RetrieveResult:
    hits: list[RetrievalHit]
    confidence: float
    elapsed_ms: float
    mode: str
    insufficient: bool = False
    grounding: float = 0.0
    semantic_score: float = 0.0
    embedding_ms: float = 0.0
    abstain_reason: str | None = None


def distinctive_query_tokens(query: str) -> set[str]:
    """Content tokens that should appear in grounded KB context."""
    toks = re.findall(r"[a-z0-9]+", query.lower())
    return {t for t in toks if len(t) > 2 and t not in _GENERIC_TOKENS}


def grounding_overlap(query: str, hits: Sequence[RetrievalHit]) -> float:
    """Fraction of distinctive query tokens found in top hit titles/bodies.

    Out-of-corpus nouns (e.g. unicorn, martian) drive this toward 0 even when
    FAISS still returns a nearest neighbor among fitness docs.

    Long distinctive tokens (len >= 5) missing from context hard-fail to 0.0 so
    compounds like "dark matter whey" or "plasma squats" abstain.

    Indonesian fitness terms are mapped to English equivalents for the check
    only (KB is English). The retrieval query itself is never translated.
    """
    from .language import expand_tokens_for_grounding

    q_tokens = distinctive_query_tokens(query)
    if not q_tokens:
        return 1.0
    if not hits:
        return 0.0
    # Map ID→EN for overlap against English chunks; keep originals too
    check_tokens = expand_tokens_for_grounding(q_tokens)
    blob_parts: list[str] = []
    for hit in hits[:5]:
        chunk = hit.chunk
        blob_parts.append(hit.citation.paragraph.lower())
        if chunk:
            blob_parts.append((chunk.title or "").lower())
            blob_parts.append((chunk.slug or "").replace("-", " ").lower())
            blob_parts.append((chunk.heading or "").lower())
    blob = " ".join(blob_parts)

    # Long-token hard fail uses expanded set so "kreatin"→"creatine" can match
    long_tokens = {t for t in check_tokens if len(t) >= 5}
    if long_tokens and any(t not in blob for t in long_tokens):
        # Allow pass if at least one long token matches AND majority of check tokens match
        long_found = sum(1 for t in long_tokens if t in blob)
        if long_found == 0:
            return 0.0
    found = sum(1 for t in check_tokens if t in blob)
    return found / len(check_tokens)


def _dedupe_key(hit: RetrievalHit, strategy: str) -> str:
    chunk = hit.chunk
    strategy = (strategy or "doc_id").lower()
    if strategy in {"none", "off", "chunk_id"}:
        return hit.chunk_id
    if strategy == "file_path":
        return (chunk.file_path if chunk else None) or hit.citation.file_path or hit.chunk_id
    # doc_id default
    if chunk and chunk.doc_id:
        return chunk.doc_id
    if chunk and chunk.file_path:
        return chunk.file_path
    return hit.citation.file_path or hit.chunk_id


def dedupe_hits(
    hits: list[RetrievalHit],
    *,
    strategy: str = "doc_id",
    top_k: int | None = None,
) -> list[RetrievalHit]:
    """Keep the highest-scoring hit per document / path / chunk."""
    if strategy.lower() in {"none", "off"}:
        out = list(hits)
        return out[:top_k] if top_k else out

    seen: set[str] = set()
    unique: list[RetrievalHit] = []
    for hit in hits:
        key = _dedupe_key(hit, strategy)
        if key in seen:
            continue
        seen.add(key)
        unique.append(hit)
        if top_k is not None and len(unique) >= top_k:
            break
    return unique


def confidence_from_hits(hits: list[RetrievalHit]) -> float:
    """Map top retrieval score to a [0, 1] confidence estimate."""
    if not hits:
        return 0.0
    raw = float(hits[0].score)
    # RRF scores are typically << 1; cosine/IP ~ [0, 1]; BGE logits can be large.
    if raw <= 1.0:
        return max(0.0, min(1.0, raw * 8.0 if raw < 0.2 else raw))
    # Cross-encoder style: sigmoid-ish squash
    import math

    return 1.0 / (1.0 + math.exp(-raw / 4.0))


class Retriever:
    """Embed query → FAISS (HNSW) search → optional BM25 fusion → dedupe → metadata."""

    def __init__(
        self,
        config: RagConfig,
        *,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self.config = config
        self._embedder_override = embedder
        self._embedder: EmbeddingProvider | None = embedder
        self.chunks: list[Chunk] = []
        self.chunk_by_id: dict[str, Chunk] = {}
        self.faiss = FaissStore(config.retrieval)
        self.bm25 = BM25Index(config.retrieval)
        self._ready = False

    def load(self) -> None:
        cfg = self.config.retrieval
        self.chunks = load_chunks_jsonl(cfg.path("chunks"))
        self.chunk_by_id = {c.chunk_id: c for c in self.chunks}
        self.faiss.load()
        mode = self.config.rag.retrieval_mode.lower()
        if mode == "hybrid":
            self.bm25.load()
        if self._embedder is None:
            self._embedder = self._embedder_override or create_embedding_provider(cfg)
        self._ready = True
        logger.info(
            "Retriever ready (%d chunks, mode=%s)",
            len(self.chunks),
            mode,
        )

    def _ensure_ready(self) -> None:
        if not self._ready:
            self.load()

    def _hit(self, chunk_id: str, score: float) -> RetrievalHit | None:
        chunk = self.chunk_by_id.get(chunk_id)
        if chunk is None:
            return None
        citation = Citation(
            file_path=chunk.file_path,
            heading=chunk.heading,
            paragraph=chunk.content,
            source=chunk.source or chunk.file_path,
            url=chunk.url,
        )
        return RetrievalHit(chunk_id=chunk_id, score=score, citation=citation, chunk=chunk)

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        mode: str | None = None,
        apply_guard: bool = True,
        language: str | None = None,
        grounding_query: str | None = None,
    ) -> RetrieveResult:
        """Run retrieval and return hits with timing + confidence.

        ``query`` is embedded / fused for search (may include conversation
        enrichment). ``grounding_query`` (default: query) is used only for the
        token-overlap abstain check so follow-up meta-text does not false-abstain.
        """
        self._ensure_ready()
        assert self._embedder is not None

        t0 = time.perf_counter()
        rag = self.config.rag
        mode_l = (mode or rag.retrieval_mode).lower()
        lang = (language or "en").lower()
        if (
            mode is None
            and mode_l == "hybrid"
            and lang != "en"
            and getattr(rag, "non_english_faiss_only", True)
        ):
            mode_l = "faiss"
        k = top_k or rag.top_k_retrieve
        rc = self.config.retrieval.retrieval
        ground_q = grounding_query if grounding_query is not None else query

        t_emb = time.perf_counter()
        qvec = self._embedder.embed([query], is_query=True)[0]
        embedding_ms = (time.perf_counter() - t_emb) * 1000.0
        semantic = self.faiss.search(qvec, top_k=max(k, rc.top_k_semantic))
        semantic_top = float(semantic[0][1]) if semantic else 0.0

        if mode_l == "faiss":
            ranked = semantic[:k]
        elif mode_l == "hybrid":
            expanded = expand_query(query)
            lexical = self.bm25.search(expanded, top_k=rc.top_k_bm25)
            ranked = fuse(
                semantic,
                lexical,
                method=rc.fusion,
                rrf_k=rc.rrf_k,
                semantic_weight=rc.semantic_weight,
                bm25_weight=rc.bm25_weight,
                top_n=max(k, rc.top_k_fused),
            )
        else:
            raise ValueError(f"Unknown retrieval_mode: {mode_l}")

        hits: list[RetrievalHit] = []
        for cid, score in ranked:
            hit = self._hit(cid, score)
            if hit:
                hits.append(hit)

        # Title boost uses the user-facing question when provided
        hits = apply_title_boost(ground_q, hits)
        if rag.dedupe_by and rag.dedupe_by.lower() not in {"none", "off"}:
            hits = dedupe_hits(hits, strategy=rag.dedupe_by, top_k=k)
        else:
            hits = list(hits)[:k]
        ground = grounding_overlap(ground_q, hits)
        conf = confidence_from_hits(hits)
        conf = max(0.0, min(1.0, 0.5 * conf + 0.5 * ground))
        elapsed = (time.perf_counter() - t0) * 1000.0

        abstain_reason = None
        sem_floor = rag.min_semantic_score
        if lang != "en":
            sem_floor = min(sem_floor, getattr(rag, "min_semantic_score_multilingual", 0.45))
        semantic_fail = sem_floor > 0 and semantic_top < sem_floor
        grounding_fail = rag.min_grounding_overlap > 0 and ground < rag.min_grounding_overlap
        if apply_guard:
            if not hits:
                abstain_reason = "no_hits"
            elif rag.confidence_threshold > 0 and hits[0].score < rag.confidence_threshold:
                abstain_reason = "low_fusion_score"
            elif semantic_fail:
                abstain_reason = "low_semantic_score"
            elif grounding_fail:
                abstain_reason = "low_grounding_overlap"
        insufficient = abstain_reason is not None

        return RetrieveResult(
            hits=[] if insufficient else hits,
            confidence=conf if not insufficient else min(conf, ground),
            elapsed_ms=elapsed,
            mode=mode_l,
            insufficient=insufficient,
            grounding=ground,
            semantic_score=semantic_top,
            embedding_ms=embedding_ms,
            abstain_reason=abstain_reason,
        )
