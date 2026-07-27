"""Centralized RAG configuration (YAML + environment overrides)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from retrieval.config import Config as RetrievalConfig
from retrieval.config import load_config as load_retrieval_config

from .dynamic_topk import DynamicTopKBands

DEFAULT_RAG_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "rag.yaml"


@dataclass
class LLMConfig:
    provider: str = "extractive"
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 800
    base_url: str | None = None
    system_prompt: str | None = None
    api_key: str | None = None


@dataclass
class RagRerankerConfig:
    provider: str | None = "noop"
    model: str = "BAAI/bge-reranker-v2-m3"
    top_k: int = 5
    batch_size: int = 16
    device: str = "auto"
    fallback_model: str = "BAAI/bge-reranker-base"


@dataclass
class ApiConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    title: str = "Fitness Knowledge RAG"
    cors_origins: list[str] = field(default_factory=lambda: ["*"])


@dataclass
class EvalConfig:
    questions_path: str = "evaluation/questions.jsonl"
    hallucination_path: str = "evaluation/hallucination_questions.jsonl"
    report_path: str = "evaluation/rag_report.md"
    confidence_report_path: str = "evaluation/confidence_report.md"
    benchmark_report_path: str = "evaluation/benchmark_phase45.md"
    min_questions: int = 100


@dataclass
class RagSettings:
    """Runtime knobs for retrieve → rerank → generate (Phase 4.5)."""

    retrieval_mode: str = "hybrid"
    top_k_retrieve: int = 20
    min_top_k: int = 3
    max_top_k: int = 10
    top_k_rerank: int = 5
    dedupe_by: str = "none"
    confidence_threshold: float = 0.015
    min_semantic_score: float = 0.55
    min_semantic_score_multilingual: float = 0.45
    min_grounding_overlap: float = 0.6
    non_english_faiss_only: bool = True
    insufficient_knowledge_message: str = (
        "I don't have enough information in my knowledge base to answer that confidently."
    )

    enable_reranker: bool = False
    enable_query_normalization: bool = True
    enable_language_detection: bool = True
    enable_dynamic_topk: bool = True
    enable_source_diversity: bool = True
    enable_conversation_context: bool = True
    structured_logging: bool = True

    max_history: int = 4
    max_chunks_per_doc: int = 2
    max_chunks_per_section: int = 1
    semantic_jaccard_max: float = 0.85

    dynamic_topk: DynamicTopKBands = field(default_factory=DynamicTopKBands)


@dataclass
class RagConfig:
    knowledge_root: Path
    retrieval: RetrievalConfig
    rag: RagSettings = field(default_factory=RagSettings)
    llm: LLMConfig = field(default_factory=LLMConfig)
    reranker: RagRerankerConfig = field(default_factory=RagRerankerConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    eval: EvalConfig = field(default_factory=EvalConfig)
    log_level: str = "INFO"
    json_logging: bool = True
    aliases_path: Path | None = None
    rag_config_path: Path | None = None

    def resolve(self, relative: str) -> Path:
        return (self.knowledge_root / relative).resolve()


def _merge_dataclass(cls: type, data: dict[str, Any] | None) -> Any:
    if not data:
        return cls()
    fields = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    cleaned = {k: v for k, v in data.items() if k in fields}
    return cls(**cleaned)


def _env_float(name: str, default: float | None = None) -> float | None:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def _env_int(name: str, default: int | None = None) -> int | None:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def _env_bool(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return None
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def apply_env_overrides(cfg: RagConfig) -> RagConfig:
    """Apply RAG_* and OpenAI-related environment variables."""
    if os.environ.get("RAG_LLM_PROVIDER"):
        cfg.llm.provider = os.environ["RAG_LLM_PROVIDER"].strip().lower()
    if os.environ.get("RAG_LLM_MODEL"):
        cfg.llm.model = os.environ["RAG_LLM_MODEL"].strip()
    if os.environ.get("RAG_LLM_BASE_URL"):
        cfg.llm.base_url = os.environ["RAG_LLM_BASE_URL"].strip()
    if os.environ.get("OPENAI_API_KEY"):
        cfg.llm.api_key = os.environ["OPENAI_API_KEY"].strip()
    if os.environ.get("OPENAI_BASE_URL") and not cfg.llm.base_url:
        cfg.llm.base_url = os.environ["OPENAI_BASE_URL"].strip()

    if os.environ.get("RAG_RETRIEVAL_MODE"):
        cfg.rag.retrieval_mode = os.environ["RAG_RETRIEVAL_MODE"].strip().lower()
    if os.environ.get("RAG_DEDUPE_BY"):
        cfg.rag.dedupe_by = os.environ["RAG_DEDUPE_BY"].strip().lower()

    for env_name, attr in [
        ("RAG_TOP_K", "top_k_retrieve"),
        ("RAG_TOP_K_RETRIEVE", "top_k_retrieve"),
        ("RAG_MIN_TOP_K", "min_top_k"),
        ("RAG_MAX_TOP_K", "max_top_k"),
        ("RAG_TOP_K_RERANK", "top_k_rerank"),
        ("RAG_RERANK_K", "top_k_rerank"),
        ("RAG_MAX_HISTORY", "max_history"),
        ("RAG_MAX_CHUNKS_PER_DOC", "max_chunks_per_doc"),
    ]:
        val = _env_int(env_name)
        if val is not None:
            setattr(cfg.rag, attr, val)

    conf = _env_float("RAG_CONFIDENCE_THRESHOLD")
    if conf is not None:
        cfg.rag.confidence_threshold = conf
    sem = _env_float("RAG_MIN_SEMANTIC_SCORE")
    if sem is not None:
        cfg.rag.min_semantic_score = sem
    ground = _env_float("RAG_MIN_GROUNDING_OVERLAP")
    if ground is not None:
        cfg.rag.min_grounding_overlap = ground

    for env_name, attr in [
        ("RAG_ENABLE_RERANKER", "enable_reranker"),
        ("ENABLE_RERANKER", "enable_reranker"),
        ("RAG_ENABLE_QUERY_NORMALIZATION", "enable_query_normalization"),
        ("ENABLE_QUERY_NORMALIZATION", "enable_query_normalization"),
        ("RAG_ENABLE_DYNAMIC_TOPK", "enable_dynamic_topk"),
        ("ENABLE_DYNAMIC_TOPK", "enable_dynamic_topk"),
        ("RAG_ENABLE_SOURCE_DIVERSITY", "enable_source_diversity"),
        ("ENABLE_SOURCE_DIVERSITY", "enable_source_diversity"),
        ("RAG_ENABLE_CONVERSATION_CONTEXT", "enable_conversation_context"),
        ("LANGUAGE_DETECTION", "enable_language_detection"),
        ("RAG_STRUCTURED_LOGGING", "structured_logging"),
    ]:
        flag = _env_bool(env_name)
        if flag is not None:
            setattr(cfg.rag, attr, flag)

    if os.environ.get("RAG_RERANKER_PROVIDER"):
        cfg.reranker.provider = os.environ["RAG_RERANKER_PROVIDER"].strip().lower()
    if os.environ.get("RAG_RERANKER_MODEL"):
        cfg.reranker.model = os.environ["RAG_RERANKER_MODEL"].strip()
    if os.environ.get("RAG_RERANKER_DEVICE"):
        cfg.reranker.device = os.environ["RAG_RERANKER_DEVICE"].strip().lower()
    batch = _env_int("RAG_RERANKER_BATCH_SIZE")
    if batch is not None:
        cfg.reranker.batch_size = batch

    if not cfg.rag.enable_reranker:
        cfg.reranker.provider = "noop"

    port = _env_int("RAG_API_PORT")
    if port is not None:
        cfg.api.port = port
    if os.environ.get("RAG_API_HOST"):
        cfg.api.host = os.environ["RAG_API_HOST"].strip()
    if os.environ.get("RAG_LOG_LEVEL") or os.environ.get("LOG_LEVEL"):
        cfg.log_level = (os.environ.get("RAG_LOG_LEVEL") or os.environ["LOG_LEVEL"]).strip().upper()

    temp = _env_float("RAG_LLM_TEMPERATURE")
    if temp is not None:
        cfg.llm.temperature = temp
    max_tok = _env_int("RAG_LLM_MAX_TOKENS")
    if max_tok is not None:
        cfg.llm.max_tokens = max_tok

    return cfg


def load_rag_config(
    config_path: str | Path | None = None,
    knowledge_root: str | Path | None = None,
    *,
    apply_env: bool = True,
) -> RagConfig:
    """Load rag.yaml, nested retrieval.yaml, then optional env overrides."""
    path = Path(config_path) if config_path else DEFAULT_RAG_CONFIG_PATH
    raw: dict[str, Any] = {}
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}

    retrieval_rel = str(raw.get("retrieval_config", "config/retrieval.yaml"))
    if path.exists():
        retrieval_path = (path.resolve().parent.parent / retrieval_rel).resolve()
        if not retrieval_path.exists():
            retrieval_path = (path.resolve().parent / Path(retrieval_rel).name).resolve()
    else:
        retrieval_path = Path(retrieval_rel)

    retrieval_cfg = load_retrieval_config(
        retrieval_path if retrieval_path.exists() else None,
        knowledge_root,
    )
    root = retrieval_cfg.knowledge_root

    logging_cfg = raw.get("logging") or {}
    rag_raw = dict(raw.get("rag") or {})
    dyn_raw = rag_raw.pop("dynamic_topk", None)
    rag_settings = _merge_dataclass(RagSettings, rag_raw)
    if dyn_raw:
        rag_settings.dynamic_topk = _merge_dataclass(DynamicTopKBands, dyn_raw)

    aliases_rel = raw.get("aliases_path", "config/aliases.yaml")
    aliases_path = (root / aliases_rel).resolve() if aliases_rel else None

    rag_cfg = RagConfig(
        knowledge_root=root,
        retrieval=retrieval_cfg,
        rag=rag_settings,
        llm=_merge_dataclass(LLMConfig, raw.get("llm")),
        reranker=_merge_dataclass(RagRerankerConfig, raw.get("reranker")),
        api=_merge_dataclass(ApiConfig, raw.get("api")),
        eval=_merge_dataclass(EvalConfig, raw.get("eval")),
        log_level=str(logging_cfg.get("level", "INFO")),
        json_logging=bool(logging_cfg.get("json", True)),
        aliases_path=aliases_path if aliases_path and aliases_path.exists() else None,
        rag_config_path=path if path.exists() else None,
    )

    rag_cfg.retrieval.retrieval.confidence_threshold = rag_cfg.rag.confidence_threshold
    if rag_cfg.rag.insufficient_knowledge_message:
        rag_cfg.retrieval.retrieval.insufficient_evidence_message = (
            rag_cfg.rag.insufficient_knowledge_message
        )

    if not rag_cfg.rag.enable_reranker:
        rag_cfg.reranker.provider = "noop"
    if rag_cfg.reranker.provider:
        rag_cfg.retrieval.reranker.provider = rag_cfg.reranker.provider
    if rag_cfg.reranker.model:
        rag_cfg.retrieval.reranker.model = rag_cfg.reranker.model
    if rag_cfg.reranker.top_k:
        rag_cfg.retrieval.reranker.top_k = rag_cfg.reranker.top_k
        rag_cfg.retrieval.retrieval.top_k_final = rag_cfg.reranker.top_k
    # Candidate pool size
    rag_cfg.retrieval.retrieval.top_k_semantic = max(
        rag_cfg.retrieval.retrieval.top_k_semantic, rag_cfg.rag.top_k_retrieve
    )
    rag_cfg.retrieval.retrieval.top_k_fused = max(
        rag_cfg.retrieval.retrieval.top_k_fused, rag_cfg.rag.top_k_retrieve
    )

    if apply_env:
        apply_env_overrides(rag_cfg)
        rag_cfg.retrieval.retrieval.confidence_threshold = rag_cfg.rag.confidence_threshold
        if not rag_cfg.rag.enable_reranker:
            rag_cfg.reranker.provider = "noop"
        if rag_cfg.reranker.provider:
            rag_cfg.retrieval.reranker.provider = rag_cfg.reranker.provider
        if rag_cfg.reranker.model:
            rag_cfg.retrieval.reranker.model = rag_cfg.reranker.model

    return rag_cfg


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
