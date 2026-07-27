"""Query normalization and exercise alias expansion (Phase 4.5)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import yaml

# Easily extendable alias map: alias → canonical phrase
DEFAULT_ALIASES: dict[str, str] = {
    "benchpress": "bench press",
    "bench-press": "bench press",
    "bb bench": "barbell bench press",
    "db bench": "dumbbell bench press",
    "rdl": "romanian deadlift",
    "rdl's": "romanian deadlift",
    "romanian dl": "romanian deadlift",
    "pullup": "pull up",
    "pullups": "pull ups",
    "pull-up": "pull up",
    "pull-ups": "pull ups",
    "chinup": "chin up",
    "chinups": "chin ups",
    "latpulldown": "lat pulldown",
    "lat pull down": "lat pulldown",
    "bw squat": "bodyweight squat",
    "body weight squat": "bodyweight squat",
    "ohp": "overhead press",
    "military press": "overhead press",
    "db row": "dumbbell row",
    "bb row": "barbell row",
    "legpress": "leg press",
    "hipthrust": "hip thrust",
    "hip thrusts": "hip thrust",
    "facepull": "face pull",
    "facepulls": "face pull",
    "ghd": "glute ham raise",
    "ssb squat": "safety bar squat",
    "hack squat": "hack squat",
    "creatine monohydrate": "creatine",
    "kreatin": "creatine",
    "whey protein": "whey protein",
}


@dataclass
class NormalizeResult:
    original: str
    normalized: str
    aliases_applied: list[str] = field(default_factory=list)


def load_aliases(path: str | Path | None = None) -> dict[str, str]:
    """Load aliases from YAML (mapping) and merge over defaults."""
    aliases = dict(DEFAULT_ALIASES)
    if path is None:
        return aliases
    p = Path(path)
    if not p.exists():
        return aliases
    with p.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    if isinstance(raw, dict):
        # Support {aliases: {...}} or flat mapping
        mapping = raw.get("aliases", raw)
        if isinstance(mapping, dict):
            for k, v in mapping.items():
                aliases[str(k).lower().strip()] = str(v).strip()
    return aliases


def _collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _strip_punct(text: str) -> str:
    # Keep word chars, spaces, and basic hyphens for alias keys we normalize later
    return re.sub(r"[^\w\s\-']+", " ", text, flags=re.UNICODE)


def apply_aliases(text: str, aliases: Mapping[str, str]) -> tuple[str, list[str]]:
    """Replace longest-matching aliases (word-boundary aware)."""
    if not aliases:
        return text, []
    # Sort longer keys first so "pull-ups" beats "pull"
    keys = sorted(aliases.keys(), key=len, reverse=True)
    applied: list[str] = []
    out = text
    for key in keys:
        pattern = re.compile(rf"(?<!\w){re.escape(key)}(?!\w)", re.IGNORECASE)
        if pattern.search(out):
            out = pattern.sub(aliases[key], out)
            applied.append(key)
    return out, applied


def normalize_query(
    query: str,
    *,
    aliases: Mapping[str, str] | None = None,
    enabled: bool = True,
) -> NormalizeResult:
    """Lowercase, unicode NFKC, punctuation/space cleanup, optional aliases."""
    original = query or ""
    if not enabled:
        return NormalizeResult(original=original, normalized=original.strip())

    text = unicodedata.normalize("NFKC", original)
    text = text.lower()
    text = _strip_punct(text)
    text = _collapse_spaces(text)
    # Compact glued forms like "benchpress" already covered by aliases;
    # also split common glued patterns: letter-digit boundaries kept as-is.
    alias_map = aliases if aliases is not None else DEFAULT_ALIASES
    text, applied = apply_aliases(text, alias_map)
    text = _collapse_spaces(text)
    return NormalizeResult(original=original, normalized=text, aliases_applied=applied)
