"""Regex and heuristic memory extraction (no LLM)."""

from __future__ import annotations

import logging
import re
from typing import Pattern

from .models import ExtractedMemory, MemoryCategory

logger = logging.getLogger(__name__)


class MemoryExtractor:
    """Extract structured fitness facts from user messages."""

    # category -> list of (compiled_pattern, value_group_or_literal)
    _PATTERNS: dict[str, list[tuple[Pattern[str], str | int]]] = {}
    _CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
        MemoryCategory.GOAL.value: (
            "goal",
            "target",
            "tujuan",
            "target saya",
            "apa goal",
            "apa tujuan",
        ),
        MemoryCategory.WEIGHT.value: (
            "berat",
            "weight",
            "bb saya",
            "bodyweight",
            "berapa berat",
        ),
        MemoryCategory.HEIGHT.value: (
            "tinggi",
            "height",
            "berapa tinggi",
        ),
        MemoryCategory.AGE.value: (
            "umur",
            "usia",
            "age",
            "berapa umur",
        ),
        MemoryCategory.INJURY.value: (
            "cedera",
            "injury",
            "sakit",
            "pain",
            "alergi cedera",
        ),
        MemoryCategory.EQUIPMENT.value: (
            "equipment",
            "alat",
            "peralatan",
            "dumbbell",
            "barbell",
        ),
        MemoryCategory.FAVORITE_EXERCISE.value: (
            "favorite exercise",
            "latihan favorit",
            "suka latihan",
            "exercise favorit",
        ),
        MemoryCategory.WORKOUT_SPLIT.value: (
            "split",
            "program",
            "rutin",
            "workout split",
        ),
        MemoryCategory.SCHEDULE.value: (
            "schedule",
            "jadwal",
            "jam gym",
            "jam latihan",
            "kapan gym",
            "biasa gym",
        ),
        MemoryCategory.SUPPLEMENT.value: (
            "supplement",
            "suplemen",
            "creatine",
            "whey",
            "protein powder",
        ),
        MemoryCategory.DIET.value: (
            "diet",
            "makan",
            "kalori",
            "calorie",
            "macros",
        ),
        MemoryCategory.RESTRICTION.value: (
            "alergi",
            "allergy",
            "allergic",
            "restriction",
            "intoleran",
            "tidak bisa makan",
        ),
        MemoryCategory.ACHIEVEMENT.value: (
            "achievement",
            "pencapaian",
            "pr ",
            "personal record",
            "rekor",
        ),
        MemoryCategory.EXPERIENCE.value: (
            "experience",
            "pengalaman",
            "beginner",
            "intermediate",
            "advanced",
            "pemula",
            "sudah gym",
        ),
    }

    def __init__(self) -> None:
        if not self._PATTERNS:
            self._PATTERNS = self._build_patterns()

    @staticmethod
    def _build_patterns() -> dict[str, list[tuple[Pattern[str], str | int]]]:
        """Compile extraction regex patterns."""
        return {
            MemoryCategory.GOAL.value: [
                (re.compile(r"\b(?:ingin|want to|mau)\s+(cutting|bulking|bulk|maintain|recomp|fat\s*loss|muscle\s*gain)\b", re.I), 1),
                (re.compile(r"\b(?:ingin|want to|mau)\s+(cut|bulk|maintain)\b", re.I), 1),
                (re.compile(r"\b(?:my\s+goal\s+is|goal\s+saya|target\s+saya|tujuan\s+saya)\s+(cutting|bulking|bulk|maintain|maintenance|recomp|strength|hypertrophy|endurance|fat\s*loss|muscle\s*gain)\b", re.I), 1),
                (re.compile(r"\b(cutting|bulking|recomp|fat\s*loss|muscle\s*gain)\b", re.I), 1),
                (re.compile(r"\b(fat\s*loss|strength|hypertrophy|endurance|maintenance)\b", re.I), 1),
                (re.compile(r"\bfocus\s+(?:on\s+)?(cutting|bulking|recomp|fat\s*loss|muscle\s*gain|strength|hypertrophy|endurance)\b", re.I), 1),
            ],
            MemoryCategory.HEIGHT.value: [
                (re.compile(r"(?:tinggi|height)\s*(?:saya|ku|me)?\s*(?:adalah|is)?\s*(\d{2,3})\s*(?:cm)?", re.I), 1),
                (re.compile(r"(\d{2,3})\s*cm\s*(?:tinggi|tall)", re.I), 1),
            ],
            MemoryCategory.WEIGHT.value: [
                (re.compile(r"(?:berat|weight|bb)\s*(?:saya|ku|badan\s*saya|body)?\s*(?:adalah|is)?\s*(\d{2,3}(?:[.,]\d+)?)\s*(?:kg|kilogram)?", re.I), 1),
                (re.compile(r"(\d{2,3}(?:[.,]\d+)?)\s*kg", re.I), 1),
            ],
            MemoryCategory.AGE.value: [
                (re.compile(r"(?:umur|usia|age)\s*(?:saya|ku)?\s*(?:adalah|is)?\s*(\d{1,2})\s*(?:tahun|years?)?", re.I), 1),
                (re.compile(r"(\d{1,2})\s*(?:tahun|years?\s*old)", re.I), 1),
            ],
            MemoryCategory.RESTRICTION.value: [
                (re.compile(r"(?:alergi|allergic\s*to|intoleran)\s+([\w\s-]+)", re.I), 1),
                (re.compile(r"(?:tidak\s*bisa\s*makan|cannot\s*eat)\s+([\w\s-]+)", re.I), 1),
            ],
            MemoryCategory.SCHEDULE.value: [
                (re.compile(r"(?:gym|latihan|workout)\s+(?:jam|at|pukul)\s*(\d{1,2})\s*(?:pagi|am|morning)?", re.I), 1),
                (re.compile(r"(?:pagi|morning)\s+(?:gym|workout|latihan)", re.I), "morning"),
                (re.compile(r"(?:sore|evening|malam|night)\s+(?:gym|workout|latihan)", re.I), "evening"),
                (re.compile(r"(?:gym|workout|latihan)\s+(?:sore|evening|malam|night)", re.I), "evening"),
                (re.compile(r"latihan\s+(?:sore|evening|malam)", re.I), "evening"),
            ],
            MemoryCategory.WORKOUT_SPLIT.value: [
                (re.compile(r"\b(push[\s-]?pull[\s-]?legs?|ppl|upper[\s/]lower|full[\s-]?body|bro[\s-]?split)\b", re.I), 1),
                (re.compile(r"(?:split|program)\s+(?:saya|ku|is)?\s*(?:adalah|is)?\s*([\w\s/-]+)", re.I), 1),
            ],
            MemoryCategory.EQUIPMENT.value: [
                (re.compile(r"(?:punya|have|menggunakan|using)\s+(dumbbell|barbell|kettlebell|resistance\s*bands?|cable\s*machine|smith\s*machine)s?", re.I), 1),
            ],
            MemoryCategory.FAVORITE_EXERCISE.value: [
                (re.compile(r"(?:favorite|favorit|suka)\s+(?:exercise|latihan|gerakan)?\s*(?:adalah|is)?\s*([\w\s-]+)", re.I), 1),
            ],
            MemoryCategory.SUPPLEMENT.value: [
                (re.compile(r"(?:minum|take|pakai|using)\s+(creatine|whey|protein\s*powder|bcaa|pre[\s-]?workout|vitamin\s*d)", re.I), 1),
            ],
            MemoryCategory.DIET.value: [
                (re.compile(r"\b(keto|low[\s-]?carb|high[\s-]?protein|vegan|vegetarian|calorie\s*deficit|calorie\s*surplus)\b", re.I), 1),
            ],
            MemoryCategory.INJURY.value: [
                (re.compile(r"(?:cedera|injury|sakit)\s+(?:di|on|at)?\s*([\w\s-]+)", re.I), 1),
            ],
            MemoryCategory.ACHIEVEMENT.value: [
                (re.compile(r"(?:pr|personal\s*record|rekor)\s+(?:deadlift|squat|bench|ohp)?\s*(\d{2,3}(?:[.,]\d+)?)\s*kg", re.I), 0),
                (re.compile(r"(?:berhasil|achieved|hit)\s+([\w\s\d.,]+)", re.I), 1),
            ],
            MemoryCategory.EXPERIENCE.value: [
                (re.compile(r"\b(beginner|intermediate|advanced|pemula|menengah|mahir)\b", re.I), 1),
                (re.compile(r"(?:sudah|been)\s+gym\s+(\d+)\s*(?:tahun|years?|bulan|months?)", re.I), 1),
            ],
        }

    def extract(self, message: str) -> list[ExtractedMemory]:
        """Extract memory facts from a user message.

        Args:
            message: Raw user text.

        Returns:
            List of extracted memories (may be empty).
        """
        text = (message or "").strip()
        if not text:
            return []

        found: list[ExtractedMemory] = []
        seen: set[tuple[str, str]] = set()

        for category, patterns in self._PATTERNS.items():
            for pattern, group in patterns:
                match = pattern.search(text)
                if not match:
                    continue
                if isinstance(group, int):
                    raw = match.group(group).strip()
                else:
                    raw = str(group)
                value = self._normalize_value(category, raw)
                key = (category, value.lower())
                if key in seen:
                    continue
                seen.add(key)
                content = f"{category}: {value}"
                importance = self._default_importance(category)
                found.append(
                    ExtractedMemory(
                        category=category,
                        value=value,
                        content=content,
                        importance=importance,
                    )
                )

        # Session-level flags (short-term hints promoted when explicit)
        session_flags = self._extract_session_flags(text)
        found.extend(session_flags)
        return found

    def infer_categories_from_query(self, query: str) -> list[str]:
        """Infer memory categories relevant to a user question."""
        q = (query or "").lower()
        categories: list[str] = []
        for category, keywords in self._CATEGORY_KEYWORDS.items():
            if any(kw in q for kw in keywords):
                categories.append(category)
        return categories

    @staticmethod
    def _normalize_value(category: str, raw: str) -> str:
        """Normalize extracted values."""
        value = raw.strip().lower()
        value = re.sub(r"\s+", " ", value)
        if category == MemoryCategory.RESTRICTION.value:
            aliases = {
                "susu": "dairy",
                "milk": "dairy",
                "gluten": "gluten",
                "kacang": "peanuts",
                "peanut": "peanuts",
                "seafood": "seafood",
                "udang": "shellfish",
                "shrimp": "shellfish",
            }
            for key, mapped in aliases.items():
                if key in value:
                    return mapped
        if category == MemoryCategory.GOAL.value:
            goal_map = {
                "fat loss": "cutting",
                "muscle gain": "bulking",
                "bulk": "bulking",
                "cut": "cutting",
            }
            return goal_map.get(value, value.replace(" ", "_"))
        if category == MemoryCategory.SCHEDULE.value and value.isdigit():
            hour = int(value)
            if hour <= 11:
                return "morning_workout"
            if hour >= 17:
                return "evening_workout"
            return f"workout_at_{hour}"
        if category == MemoryCategory.SCHEDULE.value and value == "evening":
            return "evening_workout"
        if category == MemoryCategory.SCHEDULE.value and value == "morning":
            return "morning_workout"
        if category in {MemoryCategory.HEIGHT.value, MemoryCategory.WEIGHT.value, MemoryCategory.AGE.value}:
            return value.replace(",", ".")
        return value

    @staticmethod
    def _default_importance(category: str) -> float:
        """Assign default importance by category."""
        high = {
            MemoryCategory.GOAL.value,
            MemoryCategory.INJURY.value,
            MemoryCategory.RESTRICTION.value,
        }
        medium = {
            MemoryCategory.WEIGHT.value,
            MemoryCategory.HEIGHT.value,
            MemoryCategory.SCHEDULE.value,
            MemoryCategory.WORKOUT_SPLIT.value,
        }
        if category in high:
            return 0.9
        if category in medium:
            return 0.7
        return 0.5

    def _extract_session_flags(self, text: str) -> list[ExtractedMemory]:
        """Extract ephemeral session hints."""
        flags: list[ExtractedMemory] = []
        lower = text.lower()
        if re.search(r"(?:gym|latihan|workout).*(?:pagi|morning|jam\s*6)", lower):
            flags.append(
                ExtractedMemory(
                    category=MemoryCategory.SESSION.value,
                    value="morning_workout=True",
                    content="session: morning_workout=True",
                    importance=0.4,
                    metadata={"session_only": True},
                )
            )
        if re.search(r"kemarin|yesterday", lower) and re.search(
            r"(?:latihan|workout|gym|bench|squat|deadlift|cardio)", lower
        ):
            workout = "workout"
            for ex in ("bench", "squat", "deadlift", "cardio", "push", "pull", "legs"):
                if ex in lower:
                    workout = ex
                    break
            flags.append(
                ExtractedMemory(
                    category=MemoryCategory.SESSION.value,
                    value=f"last_workout={workout}",
                    content=f"session: last_workout={workout}",
                    importance=0.4,
                    metadata={"session_only": True},
                )
            )
        return flags
