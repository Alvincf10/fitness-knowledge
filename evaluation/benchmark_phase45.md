# Phase 4.5 Production Benchmark

## Summary

| Metric | Value | Target |
|--------|------:|-------:|
| Recall@5 | 0.9900 | ≥ 0.99 |
| Recall@10 | 0.9900 | ≥ 0.99 |
| MRR | 0.8883 | ≥ 0.98 |
| Hit Rate | 0.9900 | — |
| Citation Accuracy | 1.0000 | = 1.00 |
| False Answer Rate | 0.0000 | ≤ 0.05 |
| Abstain Rate | 1.0000 | ≥ 0.95 |
| Cross-language retrieval | 1.0000 | ≥ 0.95 |
| Follow-up success | 1.0000 | — |
| Mean retrieval (ms) | 12.6 | < 50 |
| Mean rerank (ms) | 0.0 | — |
| Mean total retrieve+rerank (ms) | 12.8 | < 100 |
| P95 total (ms) | 17.4 | — |

## Coverage

- English retrieval questions: **100**
- Indonesian pair checks: **3**
- Hallucination / OOD questions: **100**

## Notes

- Cross-encoder reranker latency depends on CPU/GPU; use `noop` for CI speed.
- Citation accuracy checks structured English file paths (never translated).
- Follow-up test: creatine → dosage enrichment via conversation context.
- MRR is below the 0.98 stretch target with multilingual MiniLM (English-only `bge-small` previously ~0.97); enable BGE reranker on GPU to recover ranking quality.

- language_detect_id: `True`
- language_detect_en: `True`
- reranker: `noop`
- enable_reranker: `False`
