"""BM25 lexical index."""

from __future__ import annotations

import logging
import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .config import Config
from .models import Chunk

logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


@dataclass
class BM25Payload:
    chunk_ids: list[str]
    corpus_tokens: list[list[str]]
    bm25: object


class BM25Index:
    """Build, persist, and query a rank_bm25 index."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.payload: BM25Payload | None = None

    def build(self, chunks: Sequence[Chunk]) -> None:
        from rank_bm25 import BM25Okapi

        chunk_ids = [c.chunk_id for c in chunks]
        corpus_tokens = [tokenize(c.content) for c in chunks]
        bm25 = BM25Okapi(corpus_tokens)
        self.payload = BM25Payload(chunk_ids=chunk_ids, corpus_tokens=corpus_tokens, bm25=bm25)
        path = self.config.path("bm25_index")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(self.payload, fh)
        logger.info("Wrote BM25 index %s (%d docs)", path, len(chunk_ids))

    def load(self) -> None:
        path = self.config.path("bm25_index")
        if not path.exists():
            raise FileNotFoundError(f"BM25 index not found: {path}")
        with path.open("rb") as fh:
            self.payload = pickle.load(fh)
        logger.info("Loaded BM25 index %s (%d docs)", path, len(self.payload.chunk_ids))

    def search(self, query: str, top_k: int = 30) -> list[tuple[str, float]]:
        if self.payload is None:
            self.load()
        assert self.payload is not None
        tokens = tokenize(query)
        if not tokens or not self.payload.chunk_ids:
            return []
        scores = self.payload.bm25.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [
            (self.payload.chunk_ids[i], float(score))
            for i, score in ranked
            if score > 0
        ]
