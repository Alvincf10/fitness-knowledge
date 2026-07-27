"""Unit tests for Phase 4 RAG pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from rag.citations import format_sources_markdown, sources_from_hits
from rag.config import load_rag_config
from rag.evaluate import generate_hallucination_questions, run_rag_evaluation
from rag.llm import ExtractiveLLM, MockLLM, create_llm
from rag.pipeline import RagPipeline
from rag.prompt_builder import build_prompt
from rag.retriever import confidence_from_hits, dedupe_hits
from retrieval.models import Chunk, Citation, RetrievalHit
from retrieval.pipeline import RetrievalPipeline
from retrieval.reranker import NoOpReranker


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
  confidence_threshold: 0.0
reranker:
  provider: noop
logging:
  level: WARNING
""",
        encoding="utf-8",
    )
    (cfg_dir / "rag.yaml").write_text(
        """
retrieval_config: config/retrieval.yaml
rag:
  retrieval_mode: hybrid
  top_k_retrieve: 5
  top_k_rerank: 3
  dedupe_by: doc_id
  confidence_threshold: 0.0
  min_semantic_score: 0.0
  min_grounding_overlap: 0.0
  insufficient_knowledge_message: Insufficient knowledge in the KB.
  enable_reranker: false
  enable_query_normalization: true
  enable_dynamic_topk: false
  enable_source_diversity: false
  enable_conversation_context: false
llm:
  provider: mock
reranker:
  provider: noop
  top_k: 3
eval:
  questions_path: evaluation/questions.jsonl
  hallucination_path: evaluation/hallucination_questions.jsonl
  report_path: evaluation/rag_report.md
  min_questions: 2
logging:
  level: WARNING
""",
        encoding="utf-8",
    )
    return tmp_path


def _build_indexes(kb_root: Path) -> None:
    from retrieval.config import load_config

    cfg = load_config(kb_root / "config" / "retrieval.yaml", kb_root)
    cfg.embedding.provider = "hash"
    RetrievalPipeline(cfg).build(force=True)


def test_dedupe_hits_by_doc_id():
    def hit(cid: str, doc: str, score: float) -> RetrievalHit:
        return RetrievalHit(
            chunk_id=cid,
            score=score,
            citation=Citation(f"{doc}.md", "H", "p", f"{doc}.md"),
            chunk=Chunk(
                chunk_id=cid,
                content="p",
                file_path=f"{doc}.md",
                heading="H",
                doc_id=doc,
            ),
        )

    hits = [hit("a#1", "docA", 0.9), hit("a#2", "docA", 0.8), hit("b#1", "docB", 0.7)]
    out = dedupe_hits(hits, strategy="doc_id", top_k=10)
    assert len(out) == 2
    assert out[0].chunk_id == "a#1"
    assert out[1].chunk_id == "b#1"


def test_confidence_from_hits_empty():
    assert confidence_from_hits([]) == 0.0


def test_prompt_builder_includes_context_and_rules():
    hits = [
        RetrievalHit(
            chunk_id="c1",
            score=0.5,
            citation=Citation("faq/protein.md", "Answer", "1.6 to 2.2 g/kg", "faq/protein.md"),
            chunk=Chunk(
                chunk_id="c1",
                content="1.6 to 2.2 g/kg",
                file_path="faq/protein.md",
                heading="Answer",
                title="How Much Protein?",
            ),
        )
    ]
    prompt = build_prompt("How much protein?", hits)
    assert "CONTEXT" in prompt.user
    assert "[1]" in prompt.user
    assert "ONLY" in prompt.system or "only" in prompt.system.lower()
    assert "faq/protein.md" in prompt.context_block


def test_citations_structured():
    hits = [
        RetrievalHit(
            chunk_id="c1",
            score=0.4,
            citation=Citation("x.md", "H", "paragraph text here", "x.md", url="https://ex"),
            chunk=Chunk(
                chunk_id="c1",
                content="paragraph text here",
                file_path="x.md",
                heading="H",
                title="X",
                category="faq",
            ),
        )
    ]
    sources = sources_from_hits(hits)
    assert sources[0].index == 1
    assert sources[0].url == "https://ex"
    assert "x.md" in format_sources_markdown(sources)


def test_extractive_llm_uses_hits():
    hits = [
        RetrievalHit(
            chunk_id="c1",
            score=1.0,
            citation=Citation("a.md", "H", "Protein target is 1.6-2.2 g/kg.", "a.md"),
            chunk=Chunk(
                chunk_id="c1",
                content="Protein target is 1.6-2.2 g/kg.",
                file_path="a.md",
                heading="H",
                title="Protein",
            ),
        )
    ]
    prompt = build_prompt("protein?", hits)
    text = ExtractiveLLM().generate(prompt, hits=hits)
    assert "[1]" in text
    assert "Protein" in text


def test_end_to_end_chat(kb_root: Path):
    _build_indexes(kb_root)
    cfg = load_rag_config(kb_root / "config" / "rag.yaml", kb_root, apply_env=False)
    cfg.llm.provider = "mock"
    cfg.rag.confidence_threshold = 0.0
    pipe = RagPipeline(cfg, llm=MockLLM("Bench press answer [1]."), reranker_backend=NoOpReranker())
    pipe.load()
    resp = pipe.chat("How do I perform the bench press?")
    assert not resp.insufficient_knowledge
    assert "Bench press" in resp.answer
    assert resp.sources
    assert resp.retrieval_ms >= 0
    assert resp.total_ms >= resp.retrieval_ms


def test_confidence_gate_abstains(kb_root: Path):
    _build_indexes(kb_root)
    cfg = load_rag_config(kb_root / "config" / "rag.yaml", kb_root, apply_env=False)
    cfg.rag.confidence_threshold = 999.0  # force abstain
    cfg.rag.min_semantic_score = 0.0
    cfg.rag.min_grounding_overlap = 0.0
    pipe = RagPipeline(cfg, llm=MockLLM(), reranker_backend=NoOpReranker())
    pipe.load()
    resp = pipe.chat("How do I perform the bench press?")
    assert resp.insufficient_knowledge
    assert "enough information" in resp.answer.lower() or "Insufficient" in resp.answer


def test_grounding_rejects_nonsense():
    from rag.retriever import grounding_overlap

    hits = [
        RetrievalHit(
            chunk_id="c1",
            score=0.5,
            citation=Citation(
                "science/training-volume.md",
                "H",
                "Weekly hard sets drive hypertrophy adaptations.",
                "science/training-volume.md",
            ),
            chunk=Chunk(
                chunk_id="c1",
                content="Weekly hard sets drive hypertrophy adaptations.",
                file_path="science/training-volume.md",
                heading="H",
                title="Training Volume",
                slug="training-volume",
            ),
        )
    ]
    assert grounding_overlap("What is training volume?", hits) >= 0.5
    assert grounding_overlap("Martian chroniton levitating unicorn protocol", hits) < 0.6
    assert grounding_overlap("dark matter whey dosage", hits) == 0.0


def test_fastapi_chat_endpoint(kb_root: Path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from rag.api import create_app

    _build_indexes(kb_root)
    cfg = load_rag_config(kb_root / "config" / "rag.yaml", kb_root, apply_env=False)
    cfg.rag.confidence_threshold = 0.0
    pipe = RagPipeline(cfg, llm=MockLLM("API answer [1]."), reranker_backend=NoOpReranker())
    pipe.load()
    app = create_app(cfg, pipeline=pipe)
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    r = client.post("/chat", json={"query": "bench press technique"})
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert "sources" in data
    assert "confidence" in data
    assert "retrieval_ms" in data
    assert "rerank_ms" in data
    assert "total_ms" in data


def test_hallucination_question_generator_min_100():
    rows = generate_hallucination_questions(n=100)
    assert len(rows) >= 100
    assert all(r["expect_abstain"] for r in rows)


def test_rag_eval_smoke(kb_root: Path):
    _build_indexes(kb_root)
    # Tiny retrieval eval set
    eval_dir = kb_root / "evaluation"
    eval_dir.mkdir(exist_ok=True)
    (eval_dir / "questions.jsonl").write_text(
        '{"id":"q1","question":"How do I perform Test Bench Press correctly?",'
        '"relevant_doc_ids":["exercise_test_bench"],'
        '"relevant_paths":["exercises/chest/test-bench-press.md"],'
        '"category":"exercise"}\n'
        '{"id":"q2","question":"How Much Protein?",'
        '"relevant_doc_ids":["faq_protein"],'
        '"relevant_paths":["faq/how-much-protein.md"],'
        '"category":"faq"}\n',
        encoding="utf-8",
    )
    cfg = load_rag_config(kb_root / "config" / "rag.yaml", kb_root, apply_env=False)
    cfg.rag.confidence_threshold = 0.0
    cfg.rag.min_semantic_score = 0.0
    cfg.rag.min_grounding_overlap = 0.0
    # Keep default gates off for tiny hash corpus; hallucination set still exercised
    cfg.eval.min_questions = 2
    pipe = RagPipeline(cfg, llm=MockLLM(), reranker_backend=NoOpReranker())
    pipe.load()
    # Raise gates only for hallucination portion by mutating after retrieval eval
    # (run_rag_evaluation uses same pipe — set moderate gates that work with hash)
    metrics = run_rag_evaluation(
        pipe,
        cfg,
        n_retrieval=2,
        n_hallucination=100,
        regenerate_hallucination=True,
    )
    assert metrics.n_retrieval == 2
    assert metrics.n_hallucination >= 100
    assert cfg.resolve(cfg.eval.report_path).exists()
    assert cfg.resolve(cfg.eval.hallucination_path).exists()


def test_create_llm_extractive():
    from rag.config import RagConfig, RagSettings, LLMConfig
    from retrieval.config import Config as RetConfig

    cfg = RagConfig(
        knowledge_root=Path("."),
        retrieval=RetConfig(),
        llm=LLMConfig(provider="extractive"),
        rag=RagSettings(),
    )
    assert create_llm(cfg).name == "extractive"
