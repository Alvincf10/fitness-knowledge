"""Fitness knowledge base indexing & retrieval engine."""

from .models import Chunk, Citation, RetrievalHit, RetrievalResult
from .pipeline import RetrievalPipeline

__all__ = [
    "Chunk",
    "Citation",
    "RetrievalHit",
    "RetrievalResult",
    "RetrievalPipeline",
]

__version__ = "0.1.0"
