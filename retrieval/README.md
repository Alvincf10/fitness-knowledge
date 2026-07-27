# Retrieval Engine

Production-grade indexing and hybrid retrieval for the Fitness Knowledge Base.

## Features

- Markdown chunker (300–500 token windows, ~50 token overlap, section hierarchy)
- Embeddings: **FastEmbed** (default), OpenAI, or deterministic hash (tests)
- FAISS vector index (HNSW default; FlatIP / IVF+PQ configurable)
- BM25 lexical index (`rank_bm25`)
- Hybrid fusion (RRF or weighted) → optional rerank → citation + hallucination guard
- Query synonym expansion for common fitness concepts
- Evaluation harness (~300 questions): Recall@5/10, MRR, Hit Rate

## Setup

```bash
cd fit-knowledge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-retrieval.txt
```

Default embedding model downloads on first FastEmbed run (`BAAI/bge-small-en-v1.5`).

Chunking is **section-based (v2)**: H2 sections are merged when small; short articles become one chunk; each chunk is prefixed with title/category. Changing chunker version auto-rebuilds chunks while keeping file-hash incremental reuse afterward.

## Configuration

See [`config/retrieval.yaml`](../config/retrieval.yaml):

| Key | Default | Notes |
|-----|---------|-------|
| `embedding.provider` | `fastembed` | `fastembed` \| `sentence_transformers` \| `openai` \| `hash` |
| `embedding.model` | `intfloat/multilingual-e5-large` | Or `BAAI/bge-m3` with `sentence_transformers` |
| `faiss.index_type` | `hnsw` | `hnsw` \| `flat_ip` \| `ivf_pq` |
| `reranker.provider` | `noop` | `noop` \| `bge` \| `jina` |
| `retrieval.fusion` | `rrf` | `rrf` \| `weighted` |
| `retrieval.confidence_threshold` | `0.015` | Below → insufficient evidence |

Docs with YAML `redirects_to` are **skipped** during ingest.

## Usage

Run from `fit-knowledge/` (or pass `--root`):

```bash
# Build chunks + embeddings + FAISS + BM25
python3 -m retrieval build

# Force full rebuild
python3 -m retrieval build --force

# Use hash embeddings (offline / CI)
python3 -m retrieval build --provider hash --force

# Query
python3 -m retrieval query "How much protein should I eat?"
python3 -m retrieval query "best chest hypertrophy exercise" --json

# Evaluate (~300 questions → evaluation/report.md)
python3 -m retrieval eval --build
```

### OpenAI embeddings

```bash
export OPENAI_API_KEY=sk-...
python3 -m retrieval build --provider openai --embed-model text-embedding-3-small --force
```

### Real rerankers

`sentence-transformers` is listed in `requirements-retrieval.txt`. Enable via config or CLI:

```yaml
reranker:
  provider: bge   # or jina
  model: BAAI/bge-reranker-base
```

```bash
python3 -m retrieval query "How much protein?" --reranker bge
```

Default remains `noop` for fast CPU eval/query loops.
## Outputs

| Path | Description |
|------|-------------|
| `data/chunks.jsonl` | Chunk records |
| `data/metadata.json` | Per-document metadata |
| `data/embeddings.npy` | Embedding matrix |
| `data/file_hashes.json` | Incremental file digests |
| `vectorstore/faiss.index` | FAISS index |
| `bm25/bm25.pkl` | BM25 index |
| `evaluation/questions.jsonl` | Benchmark questions |
| `evaluation/report.md` | Metrics report |

## Incremental rebuilds

File SHA-256 hashes and per-chunk content hashes skip unchanged documents/chunks on subsequent `build` runs. Use `--force` to recompute everything.

## Tests

```bash
cd fit-knowledge
PYTHONPATH=. pytest tests/retrieval -q
```

## Python API

```python
from retrieval import RetrievalPipeline
from retrieval.config import load_config

cfg = load_config()
pipe = RetrievalPipeline(cfg)
pipe.load()  # or pipe.build()
result = pipe.retrieve("What is progressive overload?")
if result.insufficient_evidence:
    print(result.message)
else:
    for hit in result.hits:
        print(hit.citation.file_path, hit.citation.heading, hit.score)
```
