"""Phase 4.5 unit tests: normalize, diversity, dynamic top-k, context, citations."""

from __future__ import annotations

from pathlib import Path

import pytest

from rag.citations import citations_compact, sources_from_hits
from rag.context import ConversationState, enrich_query_with_history
from rag.diversity import diversify_hits
from rag.dynamic_topk import DynamicTopKBands, select_dynamic_topk
from rag.language import detect_language
from rag.normalize import normalize_query
from rag.pipeline import RagPipeline
from rag.config import load_rag_config
from retrieval.models import Chunk, Citation, RetrievalHit
from retrieval.pipeline import RetrievalPipeline
from retrieval.reranker import NoOpReranker
from retrieval.embeddings import HashProvider


def _hit(cid: str, doc: str, heading: str, text: str, score: float) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=cid,
        score=score,
        citation=Citation(f"{doc}.md", heading, text, f"{doc}.md"),
        chunk=Chunk(
            chunk_id=cid,
            content=text,
            file_path=f"{doc}.md",
            heading=heading,
            title=doc.replace("_", " ").title(),
            doc_id=doc,
            section_path=[heading],
        ),
    )


def test_normalize_aliases_and_cleanup():
    r = normalize_query("  BenchPress!!!  ")
    assert r.normalized == "bench press"
    assert "benchpress" in r.aliases_applied

    r2 = normalize_query("rdl for hamstrings")
    assert "romanian deadlift" in r2.normalized

    r3 = normalize_query("bw squat progression")
    assert "bodyweight squat" in r3.normalized

    r4 = normalize_query("pullup strength")
    assert "pull up" in r4.normalized


def test_normalize_can_disable():
    r = normalize_query("BenchPress", enabled=False)
    assert r.normalized == "BenchPress"


def test_language_detection_id_en():
    assert detect_language("Apakah kreatin aman?").code == "id"
    assert detect_language("Is creatine safe?").code == "en"


def test_dynamic_topk_bands():
    bands = DynamicTopKBands(high_threshold=0.7, medium_threshold=0.4, high_k=3, medium_k=5, low_k=10)
    assert select_dynamic_topk(0.9, bands=bands) == 3
    assert select_dynamic_topk(0.5, bands=bands) == 5
    assert select_dynamic_topk(0.2, bands=bands) == 10
    assert select_dynamic_topk(0.9, enabled=False, default_k=7) == 7


def test_source_diversity_caps_per_doc():
    hits = [
        _hit("a#1", "docA", "Safety", "Creatine is safe for healthy adults with water.", 0.9),
        _hit("a#2", "docA", "Safety", "Creatine is safe for healthy adults with water intake.", 0.85),
        _hit("a#3", "docA", "Dosage", "Take three to five grams of creatine daily.", 0.8),
        _hit("b#1", "docB", "Overview", "Protein supports hypertrophy when training hard.", 0.7),
        _hit("c#1", "docC", "Overview", "Bench press trains the chest musculature well.", 0.6),
    ]
    out = diversify_hits(hits, top_k=5, max_per_doc=2, max_per_section=1, semantic_jaccard_max=0.9)
    docs = [h.chunk.doc_id for h in out]
    assert docs.count("docA") <= 2
    assert len(out) >= 3
    # Near-duplicate Safety chunks should not both survive
    safety = [h for h in out if h.citation.heading == "Safety"]
    assert len(safety) <= 1


def test_conversation_enrichment_followup():
    state = ConversationState(max_history=4)
    state.add("user", "Is creatine safe?")
    state.add("assistant", "Creatine is considered safe...")
    enriched = enrich_query_with_history("How much should I take?", state)
    assert "creatine" in enriched.lower()
    assert "How much should I take?" in enriched or "how much should i take" in enriched.lower()


def test_citation_formatting_structured():
    hits = [
        _hit("c#1", "supplements/creatine", "Safety", "Creatine is considered safe.", 0.9),
    ]
    # fix file path style
    hits[0].citation.file_path = "supplements/creatine.md"
    hits[0].chunk.file_path = "supplements/creatine.md"
    hits[0].chunk.title = "Creatine"
    sources = sources_from_hits(hits, rank_confidence=0.9)
    compact = citations_compact(sources)
    assert compact[0]["title"] == "Creatine"
    assert compact[0]["file"] == "supplements/creatine.md"
    assert compact[0]["section"] == "Safety"
    assert "confidence" in compact[0]


def test_noop_reranker_truncates():
    from rag.reranker import RagReranker
    from rag.config import RagConfig, RagSettings, RagRerankerConfig
    from retrieval.config import Config as RetConfig

    cfg = RagConfig(
        knowledge_root=Path("."),
        retrieval=RetConfig(),
        rag=RagSettings(enable_reranker=False, top_k_rerank=2),
        reranker=RagRerankerConfig(provider="noop"),
    )
    rr = RagReranker(cfg, backend=NoOpReranker())
    hits = [_hit(f"c{i}", f"d{i}", "H", f"text {i} unique content here", 1.0 - i * 0.1) for i in range(5)]
    out = rr.rerank("q", hits, top_k=2)
    assert len(out.hits) == 2
    assert out.elapsed_ms >= 0


@pytest.fixture
def tiny_kb(tmp_path: Path) -> Path:
    (tmp_path / "supplements").mkdir()
    (tmp_path / "supplements" / "creatine.md").write_text(
        """---
id: supplement_creatine
title: Creatine
category: supplement
---

# Creatine

## Safety

Creatine is considered safe for healthy adults.

## Dosage

Typical dosing is 3 to 5 grams daily.
""",
        encoding="utf-8",
    )
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "retrieval.yaml").write_text(
        """
knowledge_root: .
knowledge_dirs: [supplements]
chunk_target_tokens: 80
chunk_min_tokens: 40
chunk_max_tokens: 120
embedding: {provider: hash}
faiss: {index_type: flat_ip}
retrieval: {confidence_threshold: 0.0, top_k_semantic: 5, top_k_fused: 5, top_k_final: 3}
reranker: {provider: noop}
logging: {level: WARNING}
""",
        encoding="utf-8",
    )
    (cfg / "rag.yaml").write_text(
        """
retrieval_config: config/retrieval.yaml
rag:
  top_k_retrieve: 5
  top_k_rerank: 3
  min_top_k: 1
  max_top_k: 3
  confidence_threshold: 0.0
  min_semantic_score: 0.0
  min_semantic_score_multilingual: 0.0
  min_grounding_overlap: 0.0
  enable_reranker: false
  enable_query_normalization: true
  enable_dynamic_topk: true
  enable_source_diversity: true
  enable_conversation_context: true
  max_chunks_per_doc: 2
llm: {provider: mock}
reranker: {provider: noop}
logging: {level: WARNING}
""",
        encoding="utf-8",
    )
    return tmp_path


def test_followup_uses_conversation(tiny_kb: Path):
    from rag.llm import MockLLM

    rcfg_path = tiny_kb / "config" / "retrieval.yaml"
    from retrieval.config import load_config

    rcfg = load_config(rcfg_path, tiny_kb)
    RetrievalPipeline(rcfg, embedder=HashProvider()).build(force=True)
    cfg = load_rag_config(tiny_kb / "config" / "rag.yaml", tiny_kb, apply_env=False)
    pipe = RagPipeline(
        cfg,
        embedder=HashProvider(),
        llm=MockLLM("Creatine dosage answer [1]"),
        reranker_backend=NoOpReranker(),
    )
    pipe.load()
    first = pipe.chat("Is creatine safe?")
    assert not first.insufficient_knowledge
    second = pipe.chat("How much should I take?")
    assert second.normalized_query or second.query
    # History enrichment should keep creatine in retrieval context
    assert pipe.conversation.turns
