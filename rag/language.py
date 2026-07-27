"""Lightweight language detection and localized RAG messages."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Indonesian function / question words that strongly signal `id`
_ID_MARKERS = {
    "apakah",
    "adakah",
    "berapa",
    "bagaimana",
    "mengapa",
    "kenapa",
    "dimana",
    "di mana",
    "kapan",
    "siapa",
    "yang",
    "untuk",
    "dari",
    "dengan",
    "pada",
    "dalam",
    "tidak",
    "bukan",
    "sudah",
    "belum",
    "bisa",
    "dapat",
    "harus",
    "perlu",
    "saya",
    "kamu",
    "anda",
    "kami",
    "mereka",
    "ini",
    "itu",
    "juga",
    "atau",
    "serta",
    "agar",
    "supaya",
    "karena",
    "sehingga",
    "kalau",
    "jika",
    "apabila",
    "latihan",
    "olahraga",
    "otot",
    "bahu",
    "dada",
    "punggung",
    "kaki",
    "lengan",
    "aman",
    "bahaya",
    "sehari",
    "minggu",
    "membentuk",
    "meningkatkan",
    "menurunkan",
    "terbaik",
    "cara",
    "gram",
    "suplemen",
    "kreatin",
    "protein",
}

_EN_MARKERS = {
    "the",
    "is",
    "are",
    "was",
    "were",
    "what",
    "how",
    "why",
    "when",
    "where",
    "which",
    "who",
    "should",
    "would",
    "could",
    "does",
    "did",
    "do",
    "can",
    "best",
    "safe",
    "daily",
    "intake",
    "exercise",
    "workout",
    "muscle",
    "chest",
    "shoulder",
    "protein",
    "creatine",
}

# Fitness lexicon: Indonesian → English (grounding / tests only — never used to
# rewrite the retrieval query).
ID_TO_EN_FITNESS: dict[str, str] = {
    "kreatin": "creatine",
    "kreatine": "creatine",
    "protein": "protein",
    "dada": "chest",
    "bahu": "shoulder",
    "punggung": "back",
    "kaki": "legs",
    "paha": "quads",
    "bokong": "glutes",
    "pantat": "glutes",
    "lengan": "arms",
    "bisep": "biceps",
    "trisep": "triceps",
    "perut": "abs",
    "inti": "core",
    "otot": "muscle",
    "latihan": "exercise",
    "olahraga": "training",
    "angkat": "lift",
    "beban": "weight",
    "set": "sets",
    "repetisi": "reps",
    "istirahat": "rest",
    "pemulihan": "recovery",
    "hipertrofi": "hypertrophy",
    "kekuatan": "strength",
    "daya": "endurance",
    "kardiovaskular": "cardio",
    "kardio": "cardio",
    "suplemen": "supplement",
    "suplementasi": "supplementation",
    "dosis": "dose",
    "aman": "safe",
    "bahaya": "safety",
    "efektif": "effective",
    "terbaik": "best",
    "membentuk": "build",
    "membangun": "build",
    "menurunkan": "loss",
    "lemak": "fat",
    "berat": "weight",
    "badan": "body",
    "tubuh": "body",
    "sehari": "daily",
    "harian": "daily",
    "mingguan": "weekly",
    "pemula": "beginner",
    "teknik": "technique",
    "bentuk": "form",
    "program": "program",
    "volume": "volume",
    "frekuensi": "frequency",
    "progresif": "progressive",
    "kelebihan": "overload",
    "gagal": "failure",
    "push": "push",
    "pull": "pull",
    "press": "press",
    "squat": "squat",
    "deadlift": "deadlift",
    "row": "row",
    "fly": "fly",
    "pulldown": "pulldown",
    "bench": "bench",
}

INSUFFICIENT_MESSAGES: dict[str, str] = {
    "en": (
        "I don't have enough information in my knowledge base to answer that confidently."
    ),
    "id": (
        "Maaf, saya belum memiliki informasi yang cukup dalam knowledge base "
        "untuk menjawab pertanyaan tersebut dengan yakin."
    ),
}

LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "id": "Indonesian",
}


@dataclass(frozen=True)
class LanguageInfo:
    """Detected user language stored on the request context."""

    code: str  # ISO-ish: en | id | …
    name: str
    confidence: float = 1.0

    def to_dict(self) -> dict[str, str | float]:
        return {"language": self.code, "language_name": self.name, "confidence": self.confidence}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def detect_language(text: str) -> LanguageInfo:
    """Detect query language. Lightweight; prefers Indonesian vs English.

    Uses optional `langdetect` when installed, otherwise a marker-word heuristic
    that is fast and dependency-free.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return LanguageInfo(code="en", name=LANGUAGE_NAMES["en"], confidence=0.0)

    # Prefer langdetect if available (still lightweight).
    try:
        from langdetect import DetectorFactory, detect_langs

        DetectorFactory.seed = 0
        ranked = detect_langs(cleaned)
        if ranked:
            top = ranked[0]
            code = top.lang
            # Map closely-related / common misses
            if code in {"id", "ms"}:  # Malay often confuses with ID for short text
                # Tie-break with Indonesian markers for short fitness queries
                toks = set(_tokens(cleaned))
                id_hits = len(toks & _ID_MARKERS)
                if code == "ms" and id_hits == 0:
                    pass
                else:
                    code = "id"
            if code not in LANGUAGE_NAMES:
                # Fall through to heuristic for unsupported codes we still label
                pass
            else:
                return LanguageInfo(
                    code=code,
                    name=LANGUAGE_NAMES[code],
                    confidence=float(top.prob),
                )
    except Exception:
        pass

    toks = set(_tokens(cleaned))
    id_score = sum(1 for t in toks if t in _ID_MARKERS)
    en_score = sum(1 for t in toks if t in _EN_MARKERS)

    # Character cues: Indonesian often has "ng" endings / "nya" / "lah"
    joined = " ".join(toks)
    if re.search(r"\b\w+nya\b", joined) or re.search(r"\b\w+kah\b", joined):
        id_score += 2
    if "apakah" in toks or "berapa" in toks or "bagaimana" in toks:
        id_score += 3

    if id_score > en_score:
        conf = min(1.0, 0.55 + 0.1 * (id_score - en_score))
        return LanguageInfo(code="id", name=LANGUAGE_NAMES["id"], confidence=conf)
    conf = min(1.0, 0.55 + 0.1 * max(0, en_score - id_score))
    return LanguageInfo(code="en", name=LANGUAGE_NAMES["en"], confidence=conf)


def insufficient_message(language: str, *, fallback: str | None = None) -> str:
    """Localized abstain message; citations / paths never localized."""
    code = (language or "en").lower()
    if code in INSUFFICIENT_MESSAGES:
        return INSUFFICIENT_MESSAGES[code]
    if fallback:
        return fallback
    return INSUFFICIENT_MESSAGES["en"]


def expand_tokens_for_grounding(tokens: set[str]) -> set[str]:
    """Add English fitness equivalents for Indonesian tokens (grounding only)."""
    expanded = set(tokens)
    for t in list(tokens):
        en = ID_TO_EN_FITNESS.get(t)
        if en:
            expanded.add(en)
    return expanded
