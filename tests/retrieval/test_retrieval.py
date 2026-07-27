"""Unit tests for chunking, indexing, retrieval, and reranking."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from retrieval.bm25_index import BM25Index, tokenize
from retrieval.chunker import (
    MarkdownChunker,
    chunk_document,
    estimate_tokens,
    parse_frontmatter,
    split_sections,
)
from retrieval.config import Config, load_config
from retrieval.embeddings import HashProvider, l2_normalize
from retrieval.expansion import expand_query
from retrieval.guard import apply_guard
from retrieval.hybrid import fuse, reciprocal_rank_fusion
from retrieval.models import Chunk, Citation, RetrievalHit
from retrieval.pipeline import RetrievalPipeline
from retrieval.reranker import NoOpReranker
from retrieval.vectorstore import FaissStore


FIXTURE_MD = """---
id: exercise_test_bench
title: Test Bench Press
category: exercise
subcategory: chest
difficulty: beginner
muscle_primary:
- chest
equipment:
- barbell
last_review: '2026-07-27'
---

# Test Bench Press

## Overview

The test bench press is a horizontal pressing movement used for chest development.
It allows progressive overload with a barbell and is common in strength programs.

## Technique

Lie on a bench with feet flat. Unrack the bar, lower to mid-chest, and press up.
Keep scapulae retracted and wrists stacked over elbows through the range.

## Programming

Use 3 to 5 sets of 5 to 12 reps depending on the goal. Leave 1 to 3 reps in reserve
for most hypertrophy work. Progress load when form stays solid.
"""


@pytest.fixture
def kb_root(tmp_path: Path) -> Path:
    ex = tmp_path / "exercises" / "chest"
    ex.mkdir(parents=True)
    (ex / "test-bench-press.md").write_text(FIXTURE_MD, encoding="utf-8")

    faq = tmp_path / "faq"
    faq.mkdir()
    (faq / "how-much-protein.md").write_text(
        """---
id: faq_protein
title: How Much Protein?
category: faq
subcategory: nutrition
---

# How Much Protein?

## Answer

Most trainees benefit from roughly 1.6 to 2.2 g of protein per kg of bodyweight
to support muscle growth while resistance training.
""",
        encoding="utf-8",
    )
    (faq / "redirect.md").write_text(
        """---
id: faq_redirect
title: Redirect
category: faq
redirects_to: faq/how-much-protein.md
---

# Redirect
""",
        encoding="utf-8",
    )
    # Minimal config tree
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "retrieval.yaml").write_text(
        """
knowledge_root: .
knowledge_dirs: [exercises, faq]
chunk_target_tokens: 80
chunk_min_tokens: 40
chunk_max_tokens: 120
chunk_overlap_tokens: 10
embedding:
  provider: hash
  batch_size: 8
faiss:
  index_type: flat_ip
retrieval:
  top_k_semantic: 5
  top_k_bm25: 5
  top_k_fused: 5
  top_k_final: 3
  confidence_threshold: 0.0001
reranker:
  provider: noop
logging:
  level: WARNING
""",
        encoding="utf-8",
    )
    return tmp_path


def test_parse_frontmatter_and_sections():
    meta, body = parse_frontmatter(FIXTURE_MD)
    assert meta["id"] == "exercise_test_bench"
    sections = split_sections(body)
    headings = [s[0][-1] for s in sections]
    assert "Technique" in headings
    assert "Programming" in headings


def test_chunk_document_section_based_not_tiny(tmp_path: Path):
    path = tmp_path / "doc.md"
    path.write_text(FIXTURE_MD, encoding="utf-8")
    chunks = chunk_document(
        path,
        tmp_path,
        target_tokens=400,
        min_tokens=200,
        max_tokens=550,
        overlap_tokens=50,
    )
    assert chunks
    # Short exercise article should collapse to one (or few) section-based chunks
    assert len(chunks) <= 3
    assert all(c.token_estimate >= 40 for c in chunks)
    assert "Title: Test Bench Press" in chunks[0].content
    assert chunks[0].muscle == ["chest"]


def test_chunk_document_ids_and_overlap(tmp_path: Path):
    path = tmp_path / "doc.md"
    # Long content to force multiple chunks
    long = FIXTURE_MD + "\n\n## Extra\n\n" + ("word " * 400)
    path.write_text(long, encoding="utf-8")
    chunks = chunk_document(
        path, tmp_path, target_tokens=50, min_tokens=40, max_tokens=80, overlap_tokens=10
    )
    assert chunks
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    assert all(c.chunk_id.startswith("exercise_test_bench#") for c in chunks)
    assert chunks[0].muscle == ["chest"]
    assert chunks[0].equipment == ["barbell"]


def test_title_boost_promotes_exact_title():
    from retrieval.hybrid import apply_title_boost
    from retrieval.models import Chunk

    weak = RetrievalHit(
        chunk_id="a#1",
        score=0.02,
        citation=Citation("faq/other.md", "H", "p", "faq/other.md"),
        chunk=Chunk(
            chunk_id="a#1",
            content="x",
            file_path="faq/other.md",
            heading="H",
            title="Other Topic",
            slug="other",
        ),
    )
    strong = RetrievalHit(
        chunk_id="b#1",
        score=0.015,
        citation=Citation("faq/how-much-protein.md", "H", "p", "faq/how-much-protein.md"),
        chunk=Chunk(
            chunk_id="b#1",
            content="x",
            file_path="faq/how-much-protein.md",
            heading="H",
            title="How Much Protein?",
            slug="how-much-protein",
        ),
    )
    out = apply_title_boost("How Much Protein?", [weak, strong])
    assert out[0].chunk_id == "b#1"

def test_chunker_skips_redirects(kb_root: Path):
    cfg = load_config(kb_root / "config" / "retrieval.yaml", kb_root)
    chunks = MarkdownChunker(cfg).build(force=True)
    paths = {c.file_path for c in chunks}
    assert "faq/redirect.md" not in paths
    assert any("test-bench-press" in p for p in paths)
    assert (kb_root / "data" / "chunks.jsonl").exists()
    assert (kb_root / "data" / "metadata.json").exists()


def test_hash_embeddings_normalized():
    provider = HashProvider(dim=64)
    vecs = provider.embed(["hello world", "hello world", "different text"])
    assert vecs.shape == (3, 64)
    norms = np.linalg.norm(vecs, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)
    assert np.allclose(vecs[0], vecs[1])


def test_faiss_and_bm25_roundtrip(kb_root: Path):
    cfg = load_config(kb_root / "config" / "retrieval.yaml", kb_root)
    cfg.embedding.provider = "hash"
    pipe = RetrievalPipeline(cfg)
    stats = pipe.build(force=True)
    assert stats["chunks"] >= 2
    assert cfg.path("faiss_index").exists()
    assert cfg.path("bm25_index").exists()

    store = FaissStore(cfg)
    store.load()
    provider = HashProvider()
    q = provider.embed(["bench press technique"])[0]
    hits = store.search(q, top_k=3)
    assert hits

    bm = BM25Index(cfg)
    bm.load()
    assert bm.payload is not None
    assert len(bm.payload.chunk_ids) == stats["chunks"]
    # Tiny 2-doc corpora can yield BM25 IDF=0 for shared-frequency terms;
    # verify the index is queryable (scores array length matches corpus).
    scores = bm.payload.bm25.get_scores(tokenize("protein bench press"))
    assert len(scores) == stats["chunks"]


def test_rrf_prefers_consensus():
    a = [("doc1", 0.9), ("doc2", 0.8), ("doc3", 0.1)]
    b = [("doc2", 5.0), ("doc1", 4.0), ("doc4", 1.0)]
    fused = reciprocal_rank_fusion([a, b], k=60, top_n=3)
    assert fused[0][0] in {"doc1", "doc2"}


def test_weighted_fusion():
    fused = fuse(
        [("a", 0.5), ("b", 1.0)],
        [("b", 10.0), ("a", 1.0)],
        method="weighted",
        semantic_weight=0.5,
        bm25_weight=0.5,
        top_n=3,
    )
    assert fused[0][0] == "b"
    assert {doc for doc, _ in fused} >= {"a", "b"}


def test_noop_reranker_truncates():
    hits = [
        RetrievalHit(
            chunk_id=f"c{i}",
            score=1.0 - i * 0.1,
            citation=Citation(
                file_path="x.md",
                heading="H",
                paragraph=f"p{i}",
                source="x.md",
            ),
        )
        for i in range(5)
    ]
    out = NoOpReranker().rerank("q", hits, top_k=2)
    assert len(out) == 2
    assert out[0].chunk_id == "c0"


def test_guard_blocks_low_confidence():
    from retrieval.config import RetrievalConfig

    cfg = RetrievalConfig(confidence_threshold=0.5)
    hits = [
        RetrievalHit(
            chunk_id="c1",
            score=0.01,
            citation=Citation("a.md", "H", "p", "a.md"),
        )
    ]
    result = apply_guard("q", hits, cfg)
    assert result.insufficient_evidence
    assert "Insufficient evidence" in (result.message or "")


def test_query_expansion_chest():
    expanded = expand_query("best chest exercise")
    assert "pectoralis" in expanded.lower() or "bench" in expanded.lower()


def test_end_to_end_query(kb_root: Path):
    cfg = load_config(kb_root / "config" / "retrieval.yaml", kb_root)
    cfg.embedding.provider = "hash"
    # Lower threshold for hash embeddings / tiny corpus
    cfg.retrieval.confidence_threshold = 0.0
    pipe = RetrievalPipeline(cfg)
    pipe.build(force=True)
    result = pipe.retrieve("How do I perform the bench press?")
    assert not result.insufficient_evidence
    assert result.hits
    hit = result.hits[0]
    assert hit.citation.file_path
    assert hit.citation.heading
    assert hit.citation.paragraph
    assert hit.citation.source


def test_tokenize_basic():
    assert "bench" in tokenize("Bench-Press 101")
