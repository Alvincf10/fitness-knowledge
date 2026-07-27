"""Embedding providers: FastEmbed, OpenAI, and deterministic Hash (tests)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from tqdm import tqdm

from .config import Config
from .models import Chunk

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    name: str = "base"
    dim: int = 384

    @abstractmethod
    def embed(self, texts: Sequence[str], *, is_query: bool = False) -> np.ndarray:
        """Return float32 array of shape (n, dim), L2-normalized."""


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return (vectors / norms).astype(np.float32)


class HashProvider(EmbeddingProvider):
    """Deterministic pseudo-embeddings for tests / offline CI."""

    name = "hash"

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def embed(self, texts: Sequence[str], *, is_query: bool = False) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
            vec = rng.standard_normal(self.dim).astype(np.float32)
            # Light bag-of-words bias so similar tokens correlate a bit
            for token in set(text.lower().split()):
                th = hashlib.md5(token.encode()).digest()
                idx = int.from_bytes(th[:4], "little") % self.dim
                vec[idx] += 1.0
            out[i] = vec
        return l2_normalize(out)


class FastEmbedProvider(EmbeddingProvider):
    name = "fastembed"

    def __init__(self, model: str = "BAAI/bge-small-en-v1.5", batch_size: int = 64) -> None:
        from fastembed import TextEmbedding

        self.model_name = model
        self.batch_size = batch_size
        self._model = TextEmbedding(model_name=model)
        # Probe dimension
        probe = list(self._model.embed(["dimension probe"]))[0]
        self.dim = int(np.asarray(probe).shape[0])

    def embed(self, texts: Sequence[str], *, is_query: bool = False) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vectors: list[np.ndarray] = []
        for vec in self._model.embed(list(texts), batch_size=self.batch_size):
            vectors.append(np.asarray(vec, dtype=np.float32))
        return l2_normalize(np.vstack(vectors))


class OpenAIProvider(EmbeddingProvider):
    name = "openai"

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        batch_size: int = 64,
        api_key: str | None = None,
    ) -> None:
        from openai import OpenAI

        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings")
        self.model_name = model
        self.batch_size = batch_size
        self._client = OpenAI(api_key=key)
        # Known dims
        self.dim = 3072 if "large" in model else 1536

    def embed(self, texts: Sequence[str], *, is_query: bool = False) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vectors: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = list(texts[i : i + self.batch_size])
            resp = self._client.embeddings.create(model=self.model_name, input=batch)
            ordered = sorted(resp.data, key=lambda d: d.index)
            vectors.extend([d.embedding for d in ordered])
        arr = np.asarray(vectors, dtype=np.float32)
        self.dim = arr.shape[1]
        return l2_normalize(arr)


def create_embedding_provider(config: Config) -> EmbeddingProvider:
    provider = config.embedding.provider.lower()
    if provider == "fastembed":
        return FastEmbedProvider(
            model=config.embedding.model,
            batch_size=config.embedding.batch_size,
        )
    if provider == "openai":
        return OpenAIProvider(
            model=config.embedding.openai_model or config.embedding.model,
            batch_size=config.embedding.batch_size,
        )
    if provider == "hash":
        return HashProvider()
    raise ValueError(f"Unknown embedding provider: {provider}")


class EmbeddingGenerator:
    """Batch-embed chunks with incremental skip via content hashes."""

    def __init__(self, config: Config, provider: EmbeddingProvider | None = None) -> None:
        self.config = config
        self.provider = provider or create_embedding_provider(config)

    def build(self, chunks: Sequence[Chunk], *, force: bool = False) -> np.ndarray:
        cfg = self.config
        emb_path = cfg.path("embeddings")
        hash_path = cfg.path("chunk_hashes")

        old_hashes: dict[str, str] = {}
        if hash_path.exists() and not force:
            with hash_path.open(encoding="utf-8") as fh:
                old_hashes = json.load(fh)

        old_matrix: np.ndarray | None = None
        if emb_path.exists() and not force:
            old_matrix = np.load(emb_path)

        # Map old chunk_id -> row (assume previous chunks.jsonl order unknown;
        # rebuild alignment from hash file order keys)
        id_to_old_row: dict[str, int] = {cid: i for i, cid in enumerate(old_hashes)}

        new_hashes: dict[str, str] = {}
        vectors: list[np.ndarray] = []
        to_embed_idx: list[int] = []
        to_embed_texts: list[str] = []
        placeholders: list[np.ndarray | None] = [None] * len(chunks)

        for i, chunk in enumerate(chunks):
            digest = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
            new_hashes[chunk.chunk_id] = digest
            if (
                not force
                and old_matrix is not None
                and old_hashes.get(chunk.chunk_id) == digest
                and chunk.chunk_id in id_to_old_row
                and id_to_old_row[chunk.chunk_id] < len(old_matrix)
            ):
                placeholders[i] = old_matrix[id_to_old_row[chunk.chunk_id]]
            else:
                to_embed_idx.append(i)
                to_embed_texts.append(chunk.content)

        logger.info(
            "Embedding %d/%d chunks with %s (%s)",
            len(to_embed_texts),
            len(chunks),
            self.provider.name,
            getattr(self.provider, "model_name", self.provider.dim),
        )

        if to_embed_texts:
            batch_size = self.config.embedding.batch_size
            embedded_parts: list[np.ndarray] = []
            ranges = range(0, len(to_embed_texts), batch_size)
            for start in tqdm(ranges, desc="embed", unit="batch"):
                batch = to_embed_texts[start : start + batch_size]
                embedded_parts.append(self.provider.embed(batch))
            embedded = np.vstack(embedded_parts) if embedded_parts else np.zeros(
                (0, self.provider.dim), dtype=np.float32
            )
            for local_i, global_i in enumerate(to_embed_idx):
                placeholders[global_i] = embedded[local_i]

        # Fill any remaining with zeros (should not happen)
        dim = self.provider.dim
        if placeholders and placeholders[0] is not None:
            dim = int(placeholders[0].shape[0])
        matrix = np.vstack(
            [p if p is not None else np.zeros(dim, dtype=np.float32) for p in placeholders]
        ).astype(np.float32)

        emb_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(emb_path, matrix)
        hash_path.parent.mkdir(parents=True, exist_ok=True)
        with hash_path.open("w", encoding="utf-8") as fh:
            # Preserve chunk_id order matching matrix rows
            ordered = {c.chunk_id: new_hashes[c.chunk_id] for c in chunks}
            json.dump(ordered, fh, indent=2)
            fh.write("\n")

        logger.info("Wrote embeddings %s shape=%s", emb_path, matrix.shape)
        return matrix
