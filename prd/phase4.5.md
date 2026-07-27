# Phase 4.5 — Production Hardening for RAG

Upgrade the Phase 4 RAG pipeline for production readiness (ranking quality, multilingual, confidence, robustness) without rewriting the architecture.

See implementation in `rag/` and config in `config/rag.yaml`.

## Commands

```bash
python3 -m retrieval build --force
python3 -m rag calibrate --no-rerank
python3 -m rag benchmark --no-rerank
# Enable cross-encoder (GPU recommended):
ENABLE_RERANKER=true RAG_RERANKER_PROVIDER=bge python3 -m rag chat "Is creatine safe?"
```

## Reports

- `evaluation/confidence_report.md`
- `evaluation/benchmark_phase45.md`
