"""FAISS vector index builders and search."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

import numpy as np

from .config import Config, FaissConfig

logger = logging.getLogger(__name__)


def _require_faiss():
    try:
        import faiss
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("faiss-cpu is required. pip install faiss-cpu") from exc
    return faiss


def build_faiss_index(vectors: np.ndarray, faiss_cfg: FaissConfig):
    """Build a FAISS index from L2-normalized float32 vectors."""
    faiss = _require_faiss()
    if vectors.ndim != 2:
        raise ValueError("vectors must be 2-D")
    n, dim = vectors.shape
    matrix = np.ascontiguousarray(vectors.astype(np.float32))
    index_type = faiss_cfg.index_type.lower()

    if index_type in {"hnsw", "hnswflat", "indexhnswflat"}:
        index = faiss.IndexHNSWFlat(dim, faiss_cfg.hnsw_m, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efConstruction = faiss_cfg.hnsw_ef_construction
        index.hnsw.efSearch = faiss_cfg.hnsw_ef_search
        index.add(matrix)
        return index

    if index_type in {"flat_ip", "flatip", "indexflatip"}:
        index = faiss.IndexFlatIP(dim)
        index.add(matrix)
        return index

    if index_type in {"ivf_pq", "ivfpq", "ivf+pq"}:
        nlist = min(faiss_cfg.ivf_nlist, max(1, n // 10) or 1)
        quantizer = faiss.IndexFlatIP(dim)
        index = faiss.IndexIVFPQ(
            quantizer,
            dim,
            nlist,
            faiss_cfg.ivf_m,
            faiss_cfg.ivf_nbits,
            faiss.METRIC_INNER_PRODUCT,
        )
        if n < nlist:
            # Fall back when corpus too small to train IVF
            logger.warning("Corpus too small for IVF+PQ (%d < %d); using FlatIP", n, nlist)
            flat = faiss.IndexFlatIP(dim)
            flat.add(matrix)
            return flat
        index.train(matrix)
        index.add(matrix)
        index.nprobe = min(16, nlist)
        return index

    raise ValueError(f"Unknown FAISS index type: {faiss_cfg.index_type}")


class FaissStore:
    """Persist and query a FAISS index aligned to chunk row order."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.index = None
        self._chunk_ids: list[str] = []

    def build(self, vectors: np.ndarray, chunk_ids: Sequence[str]) -> None:
        self.index = build_faiss_index(vectors, self.config.faiss)
        self._chunk_ids = list(chunk_ids)
        path = self.config.path("faiss_index")
        path.parent.mkdir(parents=True, exist_ok=True)
        faiss = _require_faiss()
        faiss.write_index(self.index, str(path))
        # Sidecar id map
        id_path = path.with_suffix(".ids.txt")
        id_path.write_text("\n".join(self._chunk_ids) + ("\n" if self._chunk_ids else ""), encoding="utf-8")
        logger.info("Wrote FAISS index %s (ntotal=%d)", path, self.index.ntotal)

    def load(self) -> None:
        faiss = _require_faiss()
        path = self.config.path("faiss_index")
        if not path.exists():
            raise FileNotFoundError(f"FAISS index not found: {path}")
        self.index = faiss.read_index(str(path))
        if self.config.faiss.index_type.lower().startswith("hnsw"):
            try:
                self.index.hnsw.efSearch = self.config.faiss.hnsw_ef_search
            except Exception:
                pass
        id_path = path.with_suffix(".ids.txt")
        if id_path.exists():
            self._chunk_ids = [line for line in id_path.read_text(encoding="utf-8").splitlines() if line]
        logger.info("Loaded FAISS index %s (ntotal=%d)", path, self.index.ntotal)

    @property
    def chunk_ids(self) -> list[str]:
        return self._chunk_ids

    def search(self, query_vec: np.ndarray, top_k: int = 30) -> list[tuple[str, float]]:
        if self.index is None:
            self.load()
        assert self.index is not None
        q = np.ascontiguousarray(query_vec.reshape(1, -1).astype(np.float32))
        k = min(top_k, self.index.ntotal) if self.index.ntotal else 0
        if k == 0:
            return []
        scores, indices = self.index.search(q, k)
        results: list[tuple[str, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            cid = self._chunk_ids[idx] if idx < len(self._chunk_ids) else str(idx)
            results.append((cid, float(score)))
        return results
