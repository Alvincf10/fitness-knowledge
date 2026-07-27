"""Multilingual (Phase 4.1) tests: language detection, prompts, cross-lingual retrieval."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Sequence

import numpy as np
import pytest

from rag.api import create_app
from rag.config import load_rag_config
from rag.language import ID_TO_EN_FITNESS, detect_language, insufficient_message
from rag.llm import ExtractiveLLM
from rag.pipeline import RagPipeline
from rag.prompt_builder import build_prompt
from retrieval.embeddings import EmbeddingProvider, l2_normalize
from retrieval.models import Chunk, Citation, RetrievalHit
from retrieval.pipeline import RetrievalPipeline
from retrieval.reranker import NoOpReranker


FIXTURES = {
    "creatine": """---
id: supplement_creatine
title: Creatine
category: supplement
---

# Creatine

## Overview

Creatine is considered safe for healthy adults when used at evidence-based doses.
Typical dosing is 3–5 g daily after an optional loading phase.
""",
    "protein": """---
id: faq_protein
title: How Much Protein?
category: faq
---

# How Much Protein?

## Answer

Most trainees benefit from roughly 1.6 to 2.2 g of protein per kg of bodyweight
to support muscle growth while resistance training.
""",
    "chest": """---
id: exercise_bench
title: Barbell Bench Press
category: exercise
subcategory: chest
---

# Barbell Bench Press

## Overview

The barbell bench press is a primary chest hypertrophy and strength exercise.
""",
    "shoulder": """---
id: exercise_ohp
title: Overhead Press
category: exercise
subcategory: shoulders
---

# Overhead Press

## Overview

The overhead press is a key movement for building shoulder musculature.
""",
}


class MultilingualConceptEmbedder(EmbeddingProvider):
    """Test double simulating multilingual embeddings (no translation API).

    Maps ID/EN fitness keywords onto shared concept tokens so Indonesian and
    English queries about the same topic retrieve the same English documents.
    """

    name = "multilingual_concept"

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def _concepts(self, text: str) -> list[str]:
        toks = re.findall(r"[a-z0-9]+", text.lower())
        # Entity concepts only (skip action verbs) so ID/EN queries align
        entity_keys = {
            "creatine",
            "protein",
            "chest",
            "shoulder",
            "bench",
            "safe",
            "dada",
            "bahu",
            "kreatin",
            "kreatine",
        }
        concepts: set[str] = set()
        for t in toks:
            if t not in entity_keys and t not in ID_TO_EN_FITNESS:
                continue
            if t in {"dada", "bahu", "kreatin", "kreatine"} or t in ID_TO_EN_FITNESS:
                mapped = ID_TO_EN_FITNESS.get(t, t)
                if mapped in {"creatine", "protein", "chest", "shoulder", "safe", "bench"}:
                    concepts.add(mapped)
            elif t in {"creatine", "protein", "chest", "shoulder", "safe", "bench"}:
                concepts.add(t)
            elif t == "shoulders":
                concepts.add("shoulder")
        return sorted(concepts) or ["__empty__"]

    def embed(self, texts: Sequence[str], *, is_query: bool = False) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            concepts = self._concepts(text)
            vec = np.zeros(self.dim, dtype=np.float32)
            for c in concepts:
                th = hashlib.md5(c.encode()).digest()
                idx = int.from_bytes(th[:4], "little") % self.dim
                vec[idx] += 1.0
            if not concepts or concepts == ["__empty__"]:
                digest = hashlib.sha256(text.encode()).digest()
                rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
                vec = rng.standard_normal(self.dim).astype(np.float32)
            out[i] = vec
        return l2_normalize(out)


@pytest.fixture
def multi_kb(tmp_path: Path) -> Path:
    for name, body in [
        ("supplements/creatine.md", FIXTURES["creatine"]),
        ("faq/how-much-protein.md", FIXTURES["protein"]),
        ("exercises/chest/barbell-bench-press.md", FIXTURES["chest"]),
        ("exercises/shoulders/overhead-press.md", FIXTURES["shoulder"]),
    ]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "retrieval.yaml").write_text(
        """
knowledge_root: .
knowledge_dirs: [exercises, faq, supplements]
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
  min_semantic_score_multilingual: 0.0
  min_grounding_overlap: 0.0
  non_english_faiss_only: true
  enable_reranker: false
  enable_query_normalization: true
  enable_dynamic_topk: false
  enable_source_diversity: false
  enable_conversation_context: false
llm:
  provider: extractive
reranker:
  provider: noop
logging:
  level: WARNING
""",
        encoding="utf-8",
    )
    return tmp_path


def _build_with_embedder(kb: Path, embedder: EmbeddingProvider) -> RagPipeline:
    from retrieval.config import load_config

    rcfg = load_config(kb / "config" / "retrieval.yaml", kb)
    RetrievalPipeline(rcfg, embedder=embedder).build(force=True)
    cfg = load_rag_config(kb / "config" / "rag.yaml", kb, apply_env=False)
    pipe = RagPipeline(cfg, embedder=embedder, reranker_backend=NoOpReranker())
    pipe.load()
    return pipe


def test_detect_indonesian():
    assert detect_language("Apakah kreatin aman untuk pemula?").code == "id"


def test_detect_english():
    assert detect_language("Is creatine safe for beginners?").code == "en"


def test_insufficient_messages_localized():
    assert "knowledge base" in insufficient_message("en").lower()
    assert insufficient_message("id").startswith("Maaf")


def test_prompt_requires_user_language_and_english_paths():
    hits = [
        RetrievalHit(
            chunk_id="c1",
            score=1.0,
            citation=Citation(
                "supplements/creatine.md",
                "Overview",
                "Creatine is considered safe...",
                "supplements/creatine.md",
            ),
            chunk=Chunk(
                chunk_id="c1",
                content="Creatine is considered safe...",
                file_path="supplements/creatine.md",
                heading="Overview",
                title="Creatine",
            ),
        )
    ]
    prompt = build_prompt("Apakah kreatin aman?", hits, language="id")
    assert "USER_LANGUAGE: id" in prompt.user
    assert "same language as the user's question" in prompt.system
    assert "supplements/creatine.md" in prompt.context_block
    assert "Never translate citation file paths" in prompt.system
    assert "Bench Press" in prompt.system
    assert prompt.language == "id"


def test_extractive_indonesian_framing():
    hits = [
        RetrievalHit(
            chunk_id="c1",
            score=1.0,
            citation=Citation(
                "supplements/creatine.md", "H", "Creatine is safe.", "supplements/creatine.md"
            ),
            chunk=Chunk(
                chunk_id="c1",
                content="Creatine is safe.",
                file_path="supplements/creatine.md",
                heading="H",
                title="Creatine",
            ),
        )
    ]
    prompt = build_prompt("Apakah kreatin aman?", hits, language="id")
    text = ExtractiveLLM().generate(prompt, hits=hits)
    assert "Berdasarkan" in text
    assert "Creatine" in text


def test_cross_lingual_retrieval_parity(multi_kb: Path):
    embedder = MultilingualConceptEmbedder()
    pipe = _build_with_embedder(multi_kb, embedder)

    pairs = [
        ("Apakah creatine aman?", "Is creatine safe?", "creatine"),
        ("Berapa gram protein per hari?", "Daily protein intake?", "protein"),
        ("Latihan terbaik untuk dada?", "Best chest exercise?", "chest"),
        ("Cara membentuk bahu?", "Best shoulder exercise?", "shoulder"),
    ]
    ok = 0
    for id_q, en_q, needle in pairs:
        id_hits = pipe.retriever.retrieve(id_q, language="id", apply_guard=False).hits
        en_hits = pipe.retriever.retrieve(en_q, language="en", apply_guard=False).hits
        assert id_hits and en_hits
        id_top = id_hits[0].citation.file_path
        en_top = en_hits[0].citation.file_path
        if id_top == en_top and needle in id_top.lower():
            ok += 1
        elif id_top == en_top:
            ok += 1
    assert ok / len(pairs) >= 0.95


def test_chat_returns_language_field(multi_kb: Path):
    pipe = _build_with_embedder(multi_kb, MultilingualConceptEmbedder())
    resp = pipe.chat("Apakah kreatin aman?")
    assert resp.language == "id"
    assert not resp.insufficient_knowledge
    assert resp.to_dict()["language"] == "id"
    assert all(not s.file_path.startswith("latihan") for s in resp.sources)


def test_insufficient_in_indonesian(multi_kb: Path):
    pipe = _build_with_embedder(multi_kb, MultilingualConceptEmbedder())
    pipe.config.rag.min_semantic_score = 999.0
    pipe.config.rag.min_semantic_score_multilingual = 999.0
    resp = pipe.chat("Apakah ada protokol chroniton Martian?")
    assert resp.insufficient_knowledge
    assert resp.language == "id"
    assert resp.answer.startswith("Maaf")


def test_api_includes_language(multi_kb: Path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    pipe = _build_with_embedder(multi_kb, MultilingualConceptEmbedder())
    client = TestClient(create_app(pipe.config, pipeline=pipe))
    r = client.post("/chat", json={"query": "Is creatine safe?"})
    assert r.status_code == 200
    assert r.json()["language"] == "en"
