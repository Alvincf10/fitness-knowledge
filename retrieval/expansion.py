"""Fitness query synonym expansion."""

from __future__ import annotations

import re
from typing import Iterable

# Curated synonym / related-term map for common fitness concepts.
SYNONYM_MAP: dict[str, list[str]] = {
    "chest": ["pectoralis", "pectorals", "pecs", "bench press", "pec fly", "push-up"],
    "pecs": ["chest", "pectoralis", "bench press"],
    "pectoralis": ["chest", "pecs", "bench press"],
    "back": ["latissimus", "lats", "rhomboids", "row", "pulldown", "pull-up"],
    "lats": ["latissimus", "back", "pulldown", "pull-up"],
    "legs": ["quadriceps", "hamstrings", "glutes", "squat", "leg press", "deadlift"],
    "quads": ["quadriceps", "legs", "squat", "leg press"],
    "hamstrings": ["legs", "romanian deadlift", "hamstring curl"],
    "glutes": ["gluteus", "hip thrust", "bridge", "squat"],
    "shoulders": ["deltoids", "delts", "overhead press", "lateral raise"],
    "delts": ["shoulders", "deltoids", "overhead press"],
    "biceps": ["arms", "curl", "chin-up"],
    "triceps": ["arms", "pushdown", "dip", "close-grip"],
    "abs": ["core", "abdominals", "crunch", "plank"],
    "core": ["abs", "abdominals", "anti-rotation"],
    "calves": ["gastrocnemius", "soleus", "calf raise"],
    "fat loss": ["weight loss", "calorie deficit", "cutting", "fat oxidation"],
    "weight loss": ["fat loss", "calorie deficit", "cutting"],
    "cutting": ["fat loss", "calorie deficit", "weight loss"],
    "bulking": ["calorie surplus", "muscle gain", "hypertrophy"],
    "muscle gain": ["hypertrophy", "muscle growth", "bulking"],
    "hypertrophy": ["muscle growth", "muscle gain", "training volume"],
    "strength": ["1rm", "progressive overload", "heavy compound"],
    "protein": ["protein intake", "amino acids", "whey", "dietary protein"],
    "creatine": ["creatine monohydrate", "phosphocreatine"],
    "cardio": ["aerobic", "endurance", "conditioning", "zone 2"],
    "progressive overload": ["overload", "progression", "load increase"],
    "rir": ["reps in reserve", "proximity to failure"],
    "reps in reserve": ["rir", "proximity to failure"],
    "failure": ["training to failure", "muscular failure", "rir 0"],
    "bench press": ["chest press", "barbell bench", "horizontal press"],
    "squat": ["back squat", "leg day", "knee dominant"],
    "deadlift": ["hip hinge", "romanian deadlift", "conventional deadlift"],
    "pull-up": ["chin-up", "vertical pull", "lat pulldown"],
    "calorie deficit": ["energy deficit", "fat loss", "cutting"],
    "calorie surplus": ["energy surplus", "bulking", "muscle gain"],
    "recomposition": ["body recomposition", "recomp", "build muscle lose fat"],
    "sleep": ["recovery", "sleep quality", "rest"],
    "warmup": ["warm-up", "activation", "mobility"],
}

_PHRASE_KEYS = sorted(SYNONYM_MAP.keys(), key=len, reverse=True)


def expand_query(query: str, *, max_extra_terms: int = 12) -> str:
    """Append synonym expansions for matched fitness concepts.

    Returns a space-joined string suitable for BM25. Dense retrieval should
    still use the original query for best semantic fidelity.
    """
    lower = query.lower()
    extras: list[str] = []
    seen = set(re.findall(r"[a-z0-9]+", lower))

    for key in _PHRASE_KEYS:
        if key in lower or all(tok in seen for tok in key.split()):
            for syn in SYNONYM_MAP[key]:
                syn_l = syn.lower()
                if syn_l not in lower and syn_l not in extras:
                    extras.append(syn_l)
                if len(extras) >= max_extra_terms:
                    break
        if len(extras) >= max_extra_terms:
            break

    if not extras:
        return query
    return f"{query} {' '.join(extras)}"


def expansion_terms(query: str) -> list[str]:
    expanded = expand_query(query)
    if expanded == query:
        return []
    original_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    return [t for t in expanded.split() if t.lower() not in original_tokens]
