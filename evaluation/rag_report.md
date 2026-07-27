# RAG Evaluation Report

- Retrieval questions: **300**
- Hallucination questions: **100**

## Retrieval

| Metric | Value |
|--------|------:|
| Recall@5 | 1.0000 |
| Recall@10 | 1.0000 |
| MRR | 0.9678 |
| Hit Rate | 1.0000 |
| Mean retrieval (ms) | 11.7 |

## Hallucination / abstention

| Metric | Value | Target |
|--------|------:|-------:|
| Abstain rate | 0.9000 | ≥ 0.90 |
| False answer rate | 0.1000 | ≤ 0.10 |
| Mean total latency (ms) | 12.2 | — |

## Notes

- llm: `extractive`
- reranker: `noop`
- retrieval_mode: `hybrid`
- confidence_threshold: `0.015`
