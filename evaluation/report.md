# Retrieval Evaluation Report

- Questions: **300**
- Embedding provider: `fastembed` (`BAAI/bge-small-en-v1.5`)
- Chunker: **v2** (section-based; 1101 chunks / 1090 docs)
- Reranker: `noop` (BGE optional via `reranker.provider: bge`)
- Fusion: `rrf` + title boost

## Metrics

| Metric | Value | Target |
|--------|------:|-------:|
| Recall@5 | 1.0000 | — |
| Recall@10 | 1.0000 | ≥ 0.90 |
| MRR | 0.9672 | ≥ 0.70 |
| Hit Rate | 1.0000 | — |

## Notes

- Relevance labels are auto-derived from source document titles/ids.
- Hallucination guard uses pre-rerank fusion scores (stable scale).
- Enable BGE for production queries: `--reranker bge` or set `reranker.provider: bge` (CPU ~20–30s/query; GPU recommended).
- Prefer project venv: `fit-knowledge/.venv/bin/python -m retrieval ...`
