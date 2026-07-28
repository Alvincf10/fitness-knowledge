"""Configuration loader for the memory engine."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .models import MemoryConfig

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "memory.yaml"


def load_memory_config(
    config_path: str | Path | None = None,
    *,
    knowledge_root: str | Path | None = None,
) -> MemoryConfig:
    """Load memory configuration from YAML with sensible defaults.

    Args:
        config_path: Optional path to ``memory.yaml``.
        knowledge_root: Optional project root for resolving relative db paths.

    Returns:
        Parsed :class:`MemoryConfig`.
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    data: dict[str, Any] = {}
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
            if isinstance(raw, dict):
                data = raw
    else:
        logger.debug("Memory config not found at %s; using defaults", path)

    cfg = MemoryConfig.from_dict(data)
    if knowledge_root and not Path(cfg.db_path).is_absolute():
        cfg.db_path = str(Path(knowledge_root) / cfg.db_path)
    return cfg
