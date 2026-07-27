# Phase 3 — Knowledge Indexing & Retrieval Engine

Objective:
Build a production-grade retrieval pipeline for the Fitness AI knowledge base.

Requirements:

## 1. Markdown Chunker
- Parse every Markdown document recursively.
- Chunk into approximately 300–500 token segments with ~50 token overlap.
- Preserve section hierarchy.
- Generate unique chunk IDs.
- Extract metadata:
  - category
  - subcategory
  - slug
  - title
  - muscle
  - equipment
  - difficulty
  - source
  - last_updated

Output:
- data/chunks.jsonl
- data/metadata.json

## 2. Embedding Generator
- Support OpenAI text-embedding-3-small and text-embedding-3-large.
- Provide local embedding option (BGE-M3 or Nomic Embed).
- Batch processing with progress reporting.
- Skip unchanged documents using file hashes.

Output:
- data/embeddings.npy

## 3. Vector Database
- Build a FAISS index.
- Default: IndexHNSWFlat.
- Configurable index type (FlatIP, HNSW, IVF+PQ).

Output:
- vectorstore/faiss.index

## 4. BM25 Index
- Build a lexical search index using rank_bm25.
- Persist index.

Output:
- bm25/bm25.pkl

## 5. Hybrid Retrieval
Implement:
- Semantic Search
- BM25 Search
- Reciprocal Rank Fusion (RRF) or weighted score fusion
- Return top 30 candidates.

## 6. Reranking
Support:
- BAAI/bge-reranker-large
- jina-reranker-v2

Input:
- Top 30 retrieved chunks

Output:
- Top 10 ranked chunks

## 7. Citation
Every retrieved chunk must include:
- file path
- heading
- paragraph
- source
- URL (if available)

## 8. Evaluation
Create a benchmark with approximately 300 fitness-related questions.

Measure:
- Recall@5
- Recall@10
- MRR
- Hit Rate

Generate:
- evaluation/report.md

## 9. Hallucination Guard
If retrieval confidence is below threshold:
- Return "Insufficient evidence found in the current knowledge base."
- Never fabricate facts.

## 10. Query Expansion
Implement synonym expansion for common fitness concepts (e.g., "chest" → "pectoralis", "bench press", "pec fly"; "fat loss" → "weight loss", "calorie deficit", etc.).

General Requirements:
- Modular architecture.
- Configuration-driven settings.
- Type hints.
- Logging.
- Unit tests for chunking, indexing, retrieval, and reranking.
- README with setup and usage instructions.
- Efficient incremental rebuilds (only process changed files).