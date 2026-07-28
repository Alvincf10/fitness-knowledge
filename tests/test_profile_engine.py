"""Unit tests for the Phase 6.5 user profile engine."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory.config import load_memory_config
from memory.manager import MemoryManager
from memory.models import MemoryRecord
from profile.confidence import ProfileConfidenceScorer
from profile.engine import UserProfileEngine
from profile.models import ProfileAttribute, UserProfile
from profile.resolver import ProfileConflictResolver
from profile.snapshot import ProfileSnapshotBuilder
from profile.updater import ProfileUpdater
from profile.validator import ProfileValidator


@pytest.fixture
def memory_manager(tmp_path: Path) -> MemoryManager:
    cfg = load_memory_config(knowledge_root=tmp_path)
    cfg.db_path = str(tmp_path / "memory.db")
    cfg.embedding_provider = "hash"
    return MemoryManager(cfg)


@pytest.fixture
def engine(memory_manager: MemoryManager) -> UserProfileEngine:
    return UserProfileEngine(memory_manager)


def make_memory(
    *,
    memory_id: int,
    category: str,
    content: str,
    importance: float = 0.7,
    age_days: int = 0,
) -> MemoryRecord:
    now = datetime.now(timezone.utc) - timedelta(days=age_days)
    return MemoryRecord(
        id=memory_id,
        user_id="u1",
        category=category,
        content=content,
        importance=importance,
        created_at=now,
        updated_at=now,
    )


class TestProfileBuilder:
    def test_build_profile_from_memories(self, engine: UserProfileEngine) -> None:
        engine.memory_manager.seed_memories(
            "u1",
            [
                {"category": "goal", "content": "goal: cutting", "importance": 0.9},
                {"category": "weight", "content": "weight: 82", "importance": 0.7},
                {"category": "height", "content": "height: 175", "importance": 0.7},
            ],
        )
        profile = engine.build_profile("u1")
        assert profile.fitness_goal.value == "cutting"
        assert profile.body_metrics.weight_kg.value == 82
        assert profile.body_metrics.height_cm.value == 175
        assert profile.confidence_score > 0.0

    def test_profile_export_compact(self, engine: UserProfileEngine) -> None:
        engine.memory_manager.seed_memories(
            "u1",
            [{"category": "goal", "content": "goal: bulking", "importance": 0.9}],
        )
        profile = engine.build_profile("u1")
        exported = profile.export_compact()
        assert exported["goal"] == "bulking"
        assert exported["version"] >= 1


class TestUpdater:
    def test_newer_goal_overrides_old(self) -> None:
        updater = ProfileUpdater()
        profile = UserProfile(user_id="u1")
        old = make_memory(memory_id=1, category="goal", content="goal: cutting", age_days=30)
        new = make_memory(memory_id=2, category="goal", content="goal: bulking", age_days=0)
        updater.apply_memory(profile, old)
        updater.apply_memory(profile, new)
        assert profile.fitness_goal.value == "bulking"

    def test_update_profile_increments_version(self, engine: UserProfileEngine) -> None:
        engine.memory_manager.seed_memories(
            "u1",
            [{"category": "goal", "content": "goal: cutting", "importance": 0.9}],
        )
        profile = engine.build_profile("u1")
        version_before = profile.version
        result = engine.update_from_memories(
            "u1",
            [make_memory(memory_id=2, category="weight", content="weight: 82")],
        )
        assert result.version == version_before + 1
        assert "body_metrics.weight_kg" in result.changed_fields

    def test_apply_all_supported_categories(self) -> None:
        updater = ProfileUpdater()
        profile = UserProfile(user_id="u1")
        memories = [
            make_memory(memory_id=1, category="experience", content="experience: intermediate"),
            make_memory(memory_id=2, category="age", content="age: 28"),
            make_memory(memory_id=3, category="schedule", content="schedule: morning_workout"),
            make_memory(memory_id=4, category="workout_split", content="workout_split: push pull legs"),
            make_memory(memory_id=5, category="diet", content="diet: keto"),
            make_memory(memory_id=6, category="equipment", content="equipment: dumbbell"),
            make_memory(memory_id=7, category="injury", content="injury: knee"),
            make_memory(memory_id=8, category="restriction", content="restriction: dairy"),
            make_memory(memory_id=9, category="supplement", content="supplement: creatine"),
            make_memory(memory_id=10, category="favorite_exercise", content="favorite_exercise: bench press"),
        ]
        for memory in memories:
            updater.apply_memory(profile, memory)
        assert profile.experience.value == "intermediate"
        assert profile.body_metrics.age.value == 28
        assert profile.schedule.value == "morning_workout"
        assert profile.current_program.value == "push pull legs"
        assert profile.nutrition_preferences["diet"].value == "keto"
        assert profile.equipment[0].value == "dumbbell"
        assert profile.injuries[0].value == "knee"
        assert profile.restrictions[0].value == "dairy"
        assert profile.supplements[0].value == "creatine"
        assert profile.favorite_exercises[0].value == "bench press"

    def test_append_unique_prefers_higher_confidence(self) -> None:
        items = [ProfileAttribute(value="dumbbell", confidence=0.2)]
        ProfileUpdater._append_unique(items, ProfileAttribute(value="dumbbell", confidence=0.8))
        assert items[0].confidence == 0.8

    def test_parse_value_numeric_and_text(self) -> None:
        assert ProfileUpdater._parse_value("weight: 82") == 82
        assert ProfileUpdater._parse_value("body_fat: 12.5") == 12.5
        assert ProfileUpdater._parse_value("goal: cutting") == "cutting"


class TestValidator:
    def test_reject_negative_height(self) -> None:
        profile = UserProfile(user_id="u1")
        profile.body_metrics.height_cm = ProfileAttribute(value=-175)
        errors = ProfileValidator().validate(profile)
        assert any("height_cm" in err for err in errors)

    def test_reject_invalid_goal(self) -> None:
        profile = UserProfile(user_id="u1")
        profile.fitness_goal = ProfileAttribute(value="teleport")
        errors = ProfileValidator().validate(profile)
        assert any("invalid goal" in err for err in errors)


class TestResolver:
    def test_verified_beats_unverified(self) -> None:
        resolver = ProfileConflictResolver()
        current = ProfileAttribute(value="cutting", confidence=0.8, verified=False)
        candidate = ProfileAttribute(value="bulking", confidence=0.78, verified=True)
        chosen = resolver.choose(current, candidate)
        assert chosen.value == "bulking"

    def test_explicit_beats_inferred(self) -> None:
        resolver = ProfileConflictResolver()
        current = ProfileAttribute(value="gym", confidence=0.8, explicit=False)
        candidate = ProfileAttribute(value="home gym", confidence=0.75, explicit=True)
        chosen = resolver.choose(current, candidate)
        assert chosen.value == "home gym"

    def test_current_kept_when_candidate_weaker(self) -> None:
        resolver = ProfileConflictResolver()
        current = ProfileAttribute(value="cutting", confidence=0.9)
        candidate = ProfileAttribute(value="bulking", confidence=0.4)
        chosen = resolver.choose(current, candidate)
        assert chosen.value == "cutting"

    def test_from_memory_maps_fields(self) -> None:
        resolver = ProfileConflictResolver()
        memory = make_memory(memory_id=7, category="goal", content="goal: cutting")
        attr = resolver.from_memory(memory, value="cutting", confidence=0.8, verified=True)
        assert attr.source_memory_id == 7
        assert attr.verified is True


class TestConfidence:
    def test_confidence_scores_are_bounded(self) -> None:
        scorer = ProfileConfidenceScorer()
        score = scorer.score(
            explicit=True,
            verified=True,
            importance=0.9,
            age_days=1.0,
        )
        assert 0.0 <= score <= 0.99
        assert score > 0.7

    def test_profile_score_averages_attributes(self) -> None:
        scorer = ProfileConfidenceScorer()
        attrs = [ProfileAttribute(value="x", confidence=0.8), ProfileAttribute(value="y", confidence=0.6)]
        assert scorer.profile_score(attrs) == pytest.approx(0.7)


class TestSnapshot:
    def test_snapshot_contains_core_sections(self, engine: UserProfileEngine) -> None:
        engine.memory_manager.seed_memories(
            "u1",
            [
                {"category": "goal", "content": "goal: cutting", "importance": 0.9},
                {"category": "weight", "content": "weight: 82"},
                {"category": "height", "content": "height: 175"},
            ],
        )
        engine.build_profile("u1")
        snapshot = engine.snapshot("u1")
        assert "## User Profile" in snapshot.text
        assert "Goal: cutting" in snapshot.text
        assert snapshot.token_estimate > 0

    def test_snapshot_handles_unknowns(self) -> None:
        snapshot = ProfileSnapshotBuilder().build(UserProfile(user_id="u1"))
        assert "Goal: Unknown" in snapshot.text
        assert "Injury: None" in snapshot.text


class TestEngine:
    def test_update_from_message(self, engine: UserProfileEngine) -> None:
        result = engine.update_from_message("u1", "Saya ingin cutting.")
        assert result.profile.fitness_goal.value == "cutting"

    def test_save_and_load_profile(self, engine: UserProfileEngine, tmp_path: Path) -> None:
        engine.memory_manager.seed_memories(
            "u1",
            [{"category": "goal", "content": "goal: cutting", "importance": 0.9}],
        )
        engine.build_profile("u1")
        path = tmp_path / "profile.json"
        engine.save_profile("u1", path)
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["goal"] == "cutting"

        other = UserProfileEngine(engine.memory_manager)
        profile = other.load_profile("u1", path)
        assert profile.fitness_goal.value == "cutting"

    def test_version_history_tracks_updates(self, engine: UserProfileEngine) -> None:
        engine.update_from_message("u1", "Saya ingin cutting.")
        engine.update_from_message("u1", "Berat saya 82 kg.")
        history = engine.version_history("u1")
        assert len(history) >= 2
        assert history[-1]["version"].startswith("v")

    def test_retrieve_with_profile_priority(self, engine: UserProfileEngine) -> None:
        engine.update_from_message("u1", "Saya ingin cutting.")
        payload = engine.retrieve_with_profile_priority("u1", "Apa goal saya?")
        assert payload["snapshot"].text.startswith("## User Profile")
        assert payload["memories"]

    def test_profile_update_latency_under_5ms(self, engine: UserProfileEngine) -> None:
        engine.update_from_message("u1", "Saya ingin cutting.")
        result = engine.update_from_memories(
            "u1",
            [make_memory(memory_id=9, category="weight", content="weight: 83")],
        )
        assert result.latency_ms < 5.0

    def test_profile_errors_and_rebuild(self, engine: UserProfileEngine) -> None:
        profile = engine.get_profile("u1", rebuild=True)
        profile.body_metrics.height_cm.value = -10
        errors = engine.profile_errors("u1")
        assert errors

    def test_load_profile_all_fields(self, engine: UserProfileEngine, tmp_path: Path) -> None:
        payload = {
            "goal": "cutting",
            "weight": 82,
            "height": 175,
            "experience": "intermediate",
            "schedule": "morning_workout",
            "current_program": "push pull legs",
            "version": 3,
        }
        path = tmp_path / "profile.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        profile = engine.load_profile("u2", path)
        assert profile.fitness_goal.value == "cutting"
        assert profile.body_metrics.weight_kg.value == 82
        assert profile.version == 3


class TestModelsAndValidator:
    def test_profile_attribute_is_set_and_to_dict(self) -> None:
        attr = ProfileAttribute(value="cutting", confidence=0.8)
        assert attr.is_set() is True
        assert attr.to_dict()["value"] == "cutting"
        assert ProfileAttribute().is_set() is False

    def test_user_profile_to_dict(self) -> None:
        profile = UserProfile(user_id="u1")
        profile.fitness_goal.value = "cutting"
        data = profile.to_dict()
        assert data["user_id"] == "u1"
        assert data["fitness_goal"]["value"] == "cutting"

    def test_validator_numeric_and_blank_list_errors(self) -> None:
        profile = UserProfile(user_id="u1")
        profile.body_metrics.weight_kg.value = "heavy"
        profile.equipment.append(ProfileAttribute(value=""))
        errors = ProfileValidator().validate(profile)
        assert any("weight_kg must be numeric" in err for err in errors)
        assert any("equipment contains blank value" in err for err in errors)


class TestIntegration:
    def test_profile_first_context_builder(self, engine: UserProfileEngine) -> None:
        from integration.pipeline_with_profile import build_profile_first_context

        engine.update_from_message("u1", "Saya ingin cutting.")
        ctx = build_profile_first_context(
            engine,
            engine.memory_manager,
            "u1",
            "Berapa protein saya?",
            knowledge_text="Protein 1.6-2.2 g/kg.",
        )
        assert "User Profile" in ctx.prompt_context
        assert "Knowledge Context" in ctx.prompt_context
        assert "Answer using all available context." in ctx.prompt_context
