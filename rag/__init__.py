"""Fitness knowledge base RAG pipeline (Phase 4)."""

from .models import ChatResponse, PromptBundle, SourceRef
from .pipeline import RagPipeline, build_default_pipeline

__all__ = [
    "ChatResponse",
    "PromptBundle",
    "SourceRef",
    "RagPipeline",
    "build_default_pipeline",
]

__version__ = "0.1.0"
