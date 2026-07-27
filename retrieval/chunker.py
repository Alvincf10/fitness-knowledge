"""Markdown chunker with section hierarchy and incremental rebuilds."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Iterator

import yaml

from .config import Config
from .models import Chunk

logger = logging.getLogger(__name__)

# Bump when chunking logic changes so incremental rebuilds re-chunk automatically.
CHUNKER_VERSION = 2

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
SLUG_RE = re.compile(r"[^a-z0-9]+")


def estimate_tokens(text: str) -> int:
    """Rough whitespace token estimate (≈ GPT tokens for English prose)."""
    return max(1, len(text.split())) if text.strip() else 0


def slugify(text: str) -> str:
    s = SLUG_RE.sub("-", text.lower().strip()).strip("-")
    return s or "section"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1)) or {}
        if not isinstance(meta, dict):
            meta = {}
    except yaml.YAMLError:
        meta = {}
    body = text[match.end() :]
    return meta, body


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def split_h2_sections(body: str) -> list[tuple[str, str]]:
    """Split body into H2-rooted sections (###+ folded into parent H2).

    Returns list of (heading_title, section_markdown) where section_markdown
    includes nested headings and body text.
    """
    matches = list(HEADING_RE.finditer(body))
    if not matches:
        content = body.strip()
        return [("Document", content)] if content else []

    # Drop leading H1 title line content into preamble / first section
    sections: list[tuple[str, str]] = []
    preamble = body[: matches[0].start()].strip()

    # Walk headings; materialize blocks at H2 boundaries (or H1 as doc title skip)
    h2_starts: list[tuple[int, str, int]] = []  # (match_idx, title, level)
    for i, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        if level <= 2:
            h2_starts.append((i, title, level))

    if not h2_starts:
        # Only ###+ headings — treat whole body as one section
        content = body.strip()
        return [("Document", content)] if content else []

    for si, (match_i, title, level) in enumerate(h2_starts):
        match = matches[match_i]
        # Content starts after this heading line
        start = match.end()
        # End at next H2/H1 heading (or EOF)
        if si + 1 < len(h2_starts):
            end = matches[h2_starts[si + 1][0]].start()
        else:
            end = len(body)
        block = body[start:end].strip()
        # Skip empty H1-only title shells when next H2 carries content
        if level == 1 and not block:
            continue
        # For H1 with body before first H2, keep as Overview
        heading = title if level == 1 else title
        if level == 1:
            heading = "Overview" if block else title
        sections.append((heading, block))

    if preamble:
        sections.insert(0, ("Introduction", preamble))

    return [(h, c) for h, c in sections if c.strip()]


def split_sections(body: str) -> list[tuple[list[str], str]]:
    """Compatibility wrapper: H2 sections as single-element paths."""
    return [([h], c) for h, c in split_h2_sections(body)]


def merge_sections(
    sections: list[tuple[str, str]],
    *,
    min_tokens: int,
    target_tokens: int,
    max_tokens: int,
) -> list[tuple[str, str]]:
    """Merge adjacent small H2 sections into coherent retrieval units.

    Keeps a section alone when it already meets min_tokens. Never merges past
    max_tokens; oversized singles are left for the splitter.
    """
    if not sections:
        return []

    merged: list[tuple[str, str]] = []
    buf_heads: list[str] = []
    buf_parts: list[str] = []
    buf_tokens = 0

    def flush() -> None:
        nonlocal buf_heads, buf_parts, buf_tokens
        if not buf_parts:
            return
        heading = " + ".join(buf_heads) if len(buf_heads) > 1 else buf_heads[0]
        text = "\n\n".join(buf_parts).strip()
        merged.append((heading, text))
        buf_heads, buf_parts, buf_tokens = [], [], 0

    for heading, content in sections:
        # Format section with its heading preserved inside the chunk body
        unit = f"## {heading}\n\n{content}".strip()
        ut = estimate_tokens(unit)

        if ut >= min_tokens and not buf_parts:
            # Large enough on its own
            if ut <= max_tokens:
                merged.append((heading, unit))
            else:
                merged.append((heading, unit))  # split later
            continue

        if buf_parts and buf_tokens + ut > max_tokens:
            flush()

        buf_heads.append(heading)
        buf_parts.append(unit)
        buf_tokens += ut

        if buf_tokens >= target_tokens:
            flush()

    flush()
    return merged


def _split_oversized(
    text: str,
    *,
    target: int,
    max_tokens: int,
    overlap: int,
) -> list[str]:
    """Split text that exceeds max_tokens on paragraph boundaries with overlap."""
    if estimate_tokens(text) <= max_tokens:
        return [text]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    def flush() -> None:
        nonlocal current, current_tokens
        if current:
            chunks.append("\n\n".join(current).strip())
            current, current_tokens = [], 0

    for para in paragraphs:
        pt = estimate_tokens(para)
        if pt > max_tokens:
            flush()
            words = para.split()
            step = max(1, target - overlap)
            for i in range(0, len(words), step):
                piece = " ".join(words[i : i + target])
                if piece.strip():
                    chunks.append(piece.strip())
            continue

        if current and current_tokens + pt > max_tokens:
            flush()
            if chunks and overlap > 0:
                seed = " ".join(chunks[-1].split()[-overlap:])
                current = [seed]
                current_tokens = estimate_tokens(seed)

        current.append(para)
        current_tokens += pt
        if current_tokens >= target:
            flush()
            if chunks and overlap > 0:
                seed = " ".join(chunks[-1].split()[-overlap:])
                current = [seed]
                current_tokens = estimate_tokens(seed)

    flush()
    return [c for c in chunks if c.strip()]


def _context_prefix(title: str, category: str | None, subcategory: str | None) -> str:
    parts = [f"Title: {title}"]
    if category:
        parts.append(f"Category: {category}")
    if subcategory:
        parts.append(f"Subcategory: {subcategory}")
    return " | ".join(parts)


def chunk_document(
    file_path: Path,
    knowledge_root: Path,
    *,
    target_tokens: int = 400,
    min_tokens: int = 300,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    """Chunk a Markdown file into section-based retrieval units."""
    text = file_path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)

    if meta.get("redirects_to"):
        logger.debug("Skipping redirect: %s -> %s", file_path, meta["redirects_to"])
        return []

    rel = str(file_path.relative_to(knowledge_root)).replace("\\", "/")
    slug = file_path.stem
    doc_id = str(meta.get("id") or slug)
    title = str(meta.get("title") or slug.replace("-", " ").title())
    category = meta.get("category")
    subcategory = meta.get("subcategory")
    difficulty = meta.get("difficulty")
    muscle = _as_list(meta.get("muscle_primary") or meta.get("muscle"))
    equipment = _as_list(meta.get("equipment"))
    last_updated = meta.get("last_review") or meta.get("updated")
    if last_updated is not None:
        last_updated = str(last_updated)
    url = meta.get("url")
    if url is not None:
        url = str(url)

    raw_sections = split_h2_sections(body)
    # Short documents: keep as a single chunk when whole body fits max
    whole = body.strip()
    # Strip leading H1 for whole-doc packing
    whole_no_h1 = re.sub(r"^#\s+.+?\n+", "", whole, count=1).strip()
    whole_tokens = estimate_tokens(whole_no_h1)

    if whole_tokens <= max_tokens and whole_no_h1:
        packed_sections = [("Full article", f"## Overview\n\n{whole_no_h1}")]
    else:
        packed_sections = merge_sections(
            raw_sections,
            min_tokens=min_tokens,
            target_tokens=target_tokens,
            max_tokens=max_tokens,
        )

    prefix = _context_prefix(
        title,
        str(category) if category else None,
        str(subcategory) if subcategory else None,
    )
    chunks: list[Chunk] = []

    for heading, section_text in packed_sections:
        heading_slug = slugify(heading.split(" + ")[0])
        pieces = _split_oversized(
            section_text,
            target=target_tokens,
            max_tokens=max_tokens,
            overlap=overlap_tokens,
        )
        for i, piece in enumerate(pieces):
            display = f"{prefix}\n\n{piece}".strip()
            chunk_id = f"{doc_id}#{heading_slug}#{i}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    content=display,
                    file_path=rel,
                    heading=heading,
                    category=str(category) if category else None,
                    subcategory=str(subcategory) if subcategory else None,
                    slug=slug,
                    title=title,
                    muscle=muscle,
                    equipment=equipment,
                    difficulty=str(difficulty) if difficulty else None,
                    source=rel,
                    last_updated=last_updated,
                    url=url,
                    doc_id=doc_id,
                    token_estimate=estimate_tokens(display),
                    section_path=[heading],
                )
            )
    return chunks


def iter_knowledge_files(cfg: Config) -> Iterator[Path]:
    root = cfg.knowledge_root
    for dirname in cfg.knowledge_dirs:
        base = root / dirname
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            if path.name.lower() in {"readme.md"}:
                continue
            yield path


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def load_chunks_jsonl(path: Path) -> list[Chunk]:
    if not path.exists():
        return []
    chunks: list[Chunk] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                chunks.append(Chunk.from_dict(json.loads(line)))
    return chunks


def write_chunks_jsonl(path: Path, chunks: list[Chunk]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")


class MarkdownChunker:
    """Parse the knowledge corpus into overlapping section-aware chunks."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def build(self, *, force: bool = False) -> list[Chunk]:
        cfg = self.config
        hash_path = cfg.path("file_hashes")
        chunks_path = cfg.path("chunks")
        meta_path = cfg.path("metadata")

        old_hashes: dict[str, str] = {} if force else load_json(hash_path)
        # Invalidate reuse when chunker strategy changes
        if old_hashes.get("__chunker_version__") != str(CHUNKER_VERSION):
            logger.info(
                "Chunker version changed (%s → %s); rechunking all documents",
                old_hashes.get("__chunker_version__"),
                CHUNKER_VERSION,
            )
            old_hashes = {}

        existing = [] if force or not old_hashes else load_chunks_jsonl(chunks_path)
        by_file: dict[str, list[Chunk]] = {}
        for ch in existing:
            by_file.setdefault(ch.file_path, []).append(ch)

        new_hashes: dict[str, str] = {"__chunker_version__": str(CHUNKER_VERSION)}
        all_chunks: list[Chunk] = []
        docs_meta: list[dict[str, Any]] = []
        changed = 0
        skipped = 0
        reused = 0

        files = list(iter_knowledge_files(cfg))
        logger.info("Scanning %d markdown files", len(files))

        for path in files:
            rel = str(path.relative_to(cfg.knowledge_root)).replace("\\", "/")
            digest = sha256_file(path)
            new_hashes[rel] = digest

            text = path.read_text(encoding="utf-8")
            meta, _ = parse_frontmatter(text)
            if meta.get("redirects_to"):
                skipped += 1
                continue

            if not force and old_hashes.get(rel) == digest and rel in by_file:
                file_chunks = by_file[rel]
                reused += 1
            else:
                file_chunks = chunk_document(
                    path,
                    cfg.knowledge_root,
                    target_tokens=cfg.chunk_target_tokens,
                    min_tokens=cfg.chunk_min_tokens,
                    max_tokens=cfg.chunk_max_tokens,
                    overlap_tokens=cfg.chunk_overlap_tokens,
                )
                changed += 1

            all_chunks.extend(file_chunks)
            if file_chunks:
                sample = file_chunks[0]
                docs_meta.append(
                    {
                        "doc_id": sample.doc_id,
                        "file_path": rel,
                        "title": sample.title,
                        "category": sample.category,
                        "subcategory": sample.subcategory,
                        "slug": sample.slug,
                        "muscle": sample.muscle,
                        "equipment": sample.equipment,
                        "difficulty": sample.difficulty,
                        "source": sample.source,
                        "last_updated": sample.last_updated,
                        "url": sample.url,
                        "chunk_count": len(file_chunks),
                        "file_hash": digest,
                    }
                )

        write_chunks_jsonl(chunks_path, all_chunks)
        save_json(
            meta_path,
            {
                "generated_by": "retrieval.chunker",
                "chunker_version": CHUNKER_VERSION,
                "document_count": len(docs_meta),
                "chunk_count": len(all_chunks),
                "skipped_redirects": skipped,
                "documents": docs_meta,
            },
        )
        save_json(hash_path, new_hashes)

        logger.info(
            "Chunked %d docs → %d chunks (changed=%d reused=%d redirects_skipped=%d)",
            len(docs_meta),
            len(all_chunks),
            changed,
            reused,
            skipped,
        )
        return all_chunks
