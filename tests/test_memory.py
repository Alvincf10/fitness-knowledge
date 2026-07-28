"""Unit tests for Phase 6 conversation memory engine."""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conversation.session import ConversationSession
from memory.config import load_memory_config
from memory.context_builder import MemoryContextBuilder
from memory.extractor import MemoryExtractor
from memory.manager import MemoryManager
from memory.models import ExtractedMemory, MemoryConfig, MemoryRecord, RankedMemory
from memory.ranker import MemoryRanker
from memory.storage import MemoryStorage
from memory.summarizer import ConversationSummarizer
from retrieval.embeddings import HashProvider


@pytest.fixture
def memory_config(tmp_path: Path) -> MemoryConfig:
    cfg = load_memory_config(knowledge_root=tmp_path)
    cfg.db_path = str(tmp_path / "memory.db")
    cfg.embedding_provider = "hash"
    cfg.embedding_dim = 384
    return cfg


@pytest.fixture
def embedder() -> HashProvider:
    return HashProvider(dim=384)


@pytest.fixture
def storage(memory_config: MemoryConfig) -> MemoryStorage:
    return MemoryStorage(memory_config.db_path)


@pytest.fixture
def manager(memory_config: MemoryConfig) -> MemoryManager:
    return MemoryManager(memory_config)


class TestMemoryExtraction:
  def test_extract_goal(self) -> None:
      ext = MemoryExtractor()
      items = ext.extract("Saya ingin cutting.")
      assert any(i.category == "goal" and "cutting" in i.value for i in items)

  def test_extract_height_weight(self) -> None:
      ext = MemoryExtractor()
      h = ext.extract("Saya tinggi 175 cm.")
      w = ext.extract("Berat saya 82 kg.")
      assert any(i.category == "height" and i.value == "175" for i in h)
      assert any(i.category == "weight" and i.value == "82" for i in w)

  def test_extract_restriction(self) -> None:
      ext = MemoryExtractor()
      items = ext.extract("Saya alergi susu.")
      assert any(i.category == "restriction" and i.value == "dairy" for i in items)

  def test_extract_schedule_session(self) -> None:
      ext = MemoryExtractor()
      items = ext.extract("Saya gym jam 6 pagi.")
      assert any("morning" in i.value for i in items)

  def test_infer_categories_from_query(self) -> None:
      ext = MemoryExtractor()
      cats = ext.infer_categories_from_query("Apa goal saya?")
      assert "goal" in cats


class TestMemoryStorage:
  def test_save_and_fetch(self, storage: MemoryStorage, embedder: HashProvider) -> None:
      extracted = ExtractedMemory(category="goal", value="cutting", content="goal: cutting")
      vec = embedder.embed([extracted.content])[0]
      saved = storage.save("u1", extracted, vec)
      assert saved.id is not None
      rows = storage.get_by_user("u1", category="goal")
      assert len(rows) == 1
      assert rows[0].content == "goal: cutting"

  def test_update_existing(self, storage: MemoryStorage, embedder: HashProvider) -> None:
      ext = ExtractedMemory(category="weight", value="80", content="weight: 80", importance=0.7)
      vec = embedder.embed([ext.content])[0]
      first = storage.save("u1", ext, vec)
      second = storage.save("u1", ext, vec)
      assert first.id == second.id
      assert storage.count("u1") == 1

  def test_cosine_similarity(self, embedder: HashProvider) -> None:
      a = embedder.embed(["goal: cutting"])[0]
      b = embedder.embed(["goal: cutting"])[0]
      c = embedder.embed(["weight: 90"])[0]
      assert MemoryStorage.cosine_similarity(a, b) > 0.99
      assert MemoryStorage.cosine_similarity(a, c) < MemoryStorage.cosine_similarity(a, b)


class TestMemoryRetrievalAndRanking:
  def test_retrieve_goal(self, manager: MemoryManager) -> None:
      manager.process_user_message("u1", "Saya ingin cutting.")
      ranked, latency = manager.retrieve_memory("u1", "Apa goal saya?")
      assert latency < 50.0
      assert ranked
      assert ranked[0].record.category == "goal"

  def test_ranker_formula(self, memory_config: MemoryConfig) -> None:
      ranker = MemoryRanker(memory_config)
      now = datetime.now(timezone.utc)
      record = MemoryRecord(
          id=1,
          user_id="u1",
          category="goal",
          content="goal: cutting",
          importance=0.9,
          created_at=now,
          updated_at=now,
      )
      old = MemoryRecord(
          id=2,
          user_id="u1",
          category="goal",
          content="goal: bulking",
          importance=0.5,
          created_at=now - timedelta(days=60),
          updated_at=now - timedelta(days=60),
      )
      ranked = ranker.rank([(record, 0.8), (old, 0.85)])
      assert ranked[0].record.id == 1
      assert ranked[0].score == pytest.approx(
          0.5 * 0.8 + 0.3 * ranked[0].recency + 0.2 * 0.9,
          rel=1e-3,
      )


class TestSummarizer:
  def test_summary_contains_goal(self, manager: MemoryManager) -> None:
      manager.process_user_message("u1", "Saya ingin cutting.")
      manager.process_user_message("u1", "Berat saya 82 kg.")
      summary = manager.summarize("u1")
      assert "cutting" in summary.current_goal
      assert any("82" in f for f in summary.important_facts)

  def test_session_facts_in_summary(self) -> None:
      sess = ConversationSession(user_id="u1")
      sess.set_fact("last_workout", "bench")
      summ = ConversationSummarizer().summarize(sess.turns, [], session_facts=sess.facts)
      assert "bench" in summ.current_progress


class TestContextBuilder:
  def test_build_context_sections(self, manager: MemoryManager) -> None:
      manager.process_user_message("u1", "Saya ingin cutting.")
      ctx = manager.build_context("Apa goal saya?", "u1", knowledge_text="KB: protein intake")
      assert "Conversation Summary" in ctx.text
      assert "Relevant User Memories" in ctx.text
      assert "Retrieved Knowledge" in ctx.text
      assert "Current Question" in ctx.text
      assert ctx.token_estimate > 0


class TestMemoryManager:
  def test_session_short_term(self, manager: MemoryManager) -> None:
      manager.process_user_message("u1", "Saya gym jam 6 pagi.")
      sess = manager.session("u1")
      assert sess.get_fact("morning_workout") == "True"

  def test_seed_memories(self, manager: MemoryManager) -> None:
      manager.seed_memories(
          "u1",
          [{"category": "goal", "value": "bulking", "content": "goal: bulking"}],
      )
      ranked, _ = manager.retrieve_memory("u1", "goal saya?")
      assert ranked[0].record.category == "goal"

  def test_reset_user(self, manager: MemoryManager) -> None:
      manager.process_user_message("u1", "Berat saya 70 kg.")
      manager.reset_user("u1")
      assert manager.storage.count("u1") == 0


class TestIntegrationBridge:
  def test_enrich_retrieval_query(self, manager: MemoryManager) -> None:
      from integration.pipeline_with_memory import enrich_retrieval_query

      manager.process_user_message("u1", "Saya ingin cutting.")
      ctx = manager.build_context("berapa protein?", "u1")
      enriched = enrich_retrieval_query("berapa protein?", ctx)
      assert "cutting" in enriched.lower()
      assert "berapa protein" in enriched


class TestPerformance:
  def test_retrieval_latency_under_10ms(self, manager: MemoryManager) -> None:
      for i in range(20):
          manager.process_user_message("perf", f"Berat saya {70 + i} kg.")
      latencies: list[float] = []
      for _ in range(50):
          _, ms = manager.retrieve_memory("perf", "Berapa berat saya?")
          latencies.append(ms)
      assert sum(latencies) / len(latencies) < 10.0
