"""Configuration loading for the retrieval pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "retrieval.yaml"


@dataclass
class EmbeddingConfig:
    provider: str = "fastembed"
    model: str = "BAAI/bge-small-en-v1.5"
    batch_size: int = 64
    openai_model: str = "text-embedding-3-small"


@dataclass
class FaissConfig:
    index_type: str = "hnsw"
    hnsw_m: int = 32
    hnsw_ef_construction: int = 200
    hnsw_ef_search: int = 64
    ivf_nlist: int = 100
    ivf_m: int = 8
    ivf_nbits: int = 8


@dataclass
class RetrievalConfig:
    top_k_semantic: int = 30
    top_k_bm25: int = 30
    top_k_fused: int = 30
    top_k_final: int = 10
    fusion: str = "rrf"
    rrf_k: int = 60
    semantic_weight: float = 0.6
    bm25_weight: float = 0.4
    confidence_threshold: float = 0.015
    insufficient_evidence_message: str = (
        "Insufficient evidence found in the current knowledge base."
    )


@dataclass
class RerankerConfig:
    provider: str = "noop"
    model: str = "BAAI/bge-reranker-large"
    top_k: int = 10


@dataclass
class PathsConfig:
    chunks: str = "data/chunks.jsonl"
    metadata: str = "data/metadata.json"
    embeddings: str = "data/embeddings.npy"
    file_hashes: str = "data/file_hashes.json"
    chunk_hashes: str = "data/chunk_hashes.json"
    faiss_index: str = "vectorstore/faiss.index"
    bm25_index: str = "bm25/bm25.pkl"
    eval_questions: str = "evaluation/questions.jsonl"
    eval_report: str = "evaluation/report.md"


@dataclass
class Config:
    knowledge_root: Path = field(default_factory=lambda: Path("."))
    knowledge_dirs: list[str] = field(
        default_factory=lambda: [
            "exercises",
            "science",
            "nutrition",
            "supplements",
            "faq",
            "anatomy",
            "injuries",
            "programming",
            "decision-trees",
        ]
    )
    chunk_target_tokens: int = 400
    chunk_min_tokens: int = 300
    chunk_max_tokens: int = 500
    chunk_overlap_tokens: int = 50
    paths: PathsConfig = field(default_factory=PathsConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    faiss: FaissConfig = field(default_factory=FaissConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    reranker: RerankerConfig = field(default_factory=RerankerConfig)
    log_level: str = "INFO"

    def resolve(self, relative: str) -> Path:
        return (self.knowledge_root / relative).resolve()

    def path(self, name: str) -> Path:
        return self.resolve(getattr(self.paths, name))


def _merge_dataclass(cls: type, data: dict[str, Any] | None) -> Any:
    if not data:
        return cls()
    fields = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    return cls(**{k: v for k, v in data.items() if k in fields})


def load_config(
    config_path: str | Path | None = None,
    knowledge_root: str | Path | None = None,
) -> Config:
    """Load YAML config and resolve knowledge_root."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    raw: dict[str, Any] = {}
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}

    root = Path(knowledge_root) if knowledge_root else Path(raw.get("knowledge_root", "."))
    if not root.is_absolute():
        # Prefer config file parent (fit-knowledge/) when relative
        base = path.resolve().parent.parent if path.exists() else Path.cwd()
        root = (base / root).resolve()

    logging_cfg = raw.get("logging") or {}
    cfg = Config(
        knowledge_root=root,
        knowledge_dirs=list(raw.get("knowledge_dirs") or Config().knowledge_dirs),
        chunk_target_tokens=int(raw.get("chunk_target_tokens", 400)),
        chunk_min_tokens=int(raw.get("chunk_min_tokens", 300)),
        chunk_max_tokens=int(raw.get("chunk_max_tokens", 500)),
        chunk_overlap_tokens=int(raw.get("chunk_overlap_tokens", 50)),
        paths=_merge_dataclass(PathsConfig, raw.get("paths")),
        embedding=_merge_dataclass(EmbeddingConfig, raw.get("embedding")),
        faiss=_merge_dataclass(FaissConfig, raw.get("faiss")),
        retrieval=_merge_dataclass(RetrievalConfig, raw.get("retrieval")),
        reranker=_merge_dataclass(RerankerConfig, raw.get("reranker")),
        log_level=str(logging_cfg.get("level", "INFO")),
    )
    return cfg


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
