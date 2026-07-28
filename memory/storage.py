"""SQLite-backed long-term memory storage."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Sequence

import numpy as np

from .models import (
    ExtractedMemory,
    MemoryRecord,
    blob_to_embedding,
    embedding_to_blob,
    utc_now,
)

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding BLOB NOT NULL,
    importance REAL NOT NULL DEFAULT 0.5,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_user ON memory(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_user_category ON memory(user_id, category);
"""


class MemoryStorage:
    """Persist user memories in SQLite with vector embeddings."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Create schema if missing."""
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _parse_ts(value: str) -> datetime:
        return datetime.fromisoformat(value)

    def save(
        self,
        user_id: str,
        extracted: ExtractedMemory,
        embedding: Sequence[float],
    ) -> MemoryRecord:
        """Insert or update a memory for a user/category pair.

        Args:
            user_id: User identifier.
            extracted: Extracted memory payload.
            embedding: Embedding vector matching storage model.

        Returns:
            Persisted :class:`MemoryRecord`.
        """
        now = utc_now()
        blob = embedding_to_blob(list(embedding))
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id FROM memory
                WHERE user_id = ? AND category = ? AND content = ?
                """,
                (user_id, extracted.category, extracted.content),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE memory
                    SET embedding = ?, importance = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (blob, extracted.importance, now.isoformat(), row["id"]),
                )
                memory_id = int(row["id"])
            else:
                cur = conn.execute(
                    """
                    INSERT INTO memory
                    (user_id, category, content, embedding, importance, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        extracted.category,
                        extracted.content,
                        blob,
                        extracted.importance,
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
                memory_id = int(cur.lastrowid)
            conn.commit()

        return MemoryRecord(
            id=memory_id,
            user_id=user_id,
            category=extracted.category,
            content=extracted.content,
            embedding=list(embedding),
            importance=extracted.importance,
            created_at=now,
            updated_at=now,
        )

    def save_batch(
        self,
        user_id: str,
        items: Sequence[tuple[ExtractedMemory, Sequence[float]]],
    ) -> list[MemoryRecord]:
        """Persist multiple memories."""
        return [self.save(user_id, ext, emb) for ext, emb in items]

    def get_by_user(self, user_id: str, *, category: str | None = None) -> list[MemoryRecord]:
        """Fetch all memories for a user, optionally filtered by category."""
        query = "SELECT * FROM memory WHERE user_id = ?"
        params: list[object] = [user_id]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_by_id(self, memory_id: int) -> MemoryRecord | None:
        """Fetch a single memory by primary key."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM memory WHERE id = ?", (memory_id,)).fetchone()
        return self._row_to_record(row) if row else None

    def delete_user(self, user_id: str) -> int:
        """Delete all memories for a user (testing helper)."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM memory WHERE user_id = ?", (user_id,))
            conn.commit()
            return int(cur.rowcount)

    def count(self, user_id: str | None = None) -> int:
        """Count stored memories."""
        with self._connect() as conn:
            if user_id:
                row = conn.execute(
                    "SELECT COUNT(*) AS c FROM memory WHERE user_id = ?", (user_id,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) AS c FROM memory").fetchone()
        return int(row["c"]) if row else 0

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=int(row["id"]),
            user_id=str(row["user_id"]),
            category=str(row["category"]),
            content=str(row["content"]),
            embedding=blob_to_embedding(row["embedding"]),
            importance=float(row["importance"]),
            created_at=self._parse_ts(str(row["created_at"])),
            updated_at=self._parse_ts(str(row["updated_at"])),
        )

    @staticmethod
    def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
        """Compute cosine similarity between two vectors."""
        va = np.asarray(a, dtype=np.float32)
        vb = np.asarray(b, dtype=np.float32)
        denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
        if denom <= 1e-12:
            return 0.0
        return float(np.dot(va, vb) / denom)
