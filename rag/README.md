# RAG Pipeline (Phase 4.5)

Production RAG over the Fitness Knowledge Base — hardened for ranking quality, multilingual queries, confidence calibration, and observability.

## Pipeline

```
query → normalize + aliases → language detect
      → conversation enrich (optional)
      → multilingual embed → FAISS (+ BM25 if EN)
      → cross-encoder rerank (optional)
      → dynamic top-k → source diversity
      → confidence gate → prompt → LLM
      → answer + structured citations + JSON trace
```

## New modules (4.5)

| Module | Role |
|--------|------|
| `normalize.py` | Unicode/punct cleanup + `config/aliases.yaml` |
| `context.py` | Follow-up query enrichment |
| `dynamic_topk.py` | Confidence → final K |
| `diversity.py` | Max 2 chunks/doc, section + Jaccard |
| `calibrate.py` | Threshold sweep → `confidence_report.md` |
| `benchmark_phase45.py` | Production suite → `benchmark_phase45.md` |
| `observability.py` | Structured JSON request traces |

## Feature flags (`config/rag.yaml` / env)

| Flag / env | Default | Effect |
|------------|---------|--------|
| `enable_reranker` / `ENABLE_RERANKER` | false | BGE cross-encoder (`bge-reranker-v2-m3`) |
| `enable_query_normalization` | true | Aliases + cleanup |
| `enable_dynamic_topk` | true | High/med/low → 3/5/10 |
| `enable_source_diversity` | true | Per-doc / section caps |
| `enable_conversation_context` | true | Follow-up enrichment |
| `CONFIDENCE_THRESHOLD` | 0.01 | From calibration |

## Commands

```bash
pip install -r requirements-rag.txt
python3 -m retrieval build --force
python3 -m rag chat "rdl cues" --json
python3 -m rag calibrate --no-rerank
python3 -m rag benchmark --no-rerank
ENABLE_RERANKER=true python3 -m rag chat "Is creatine safe?"
python3 -m rag serve --port 8080
```

`POST /chat` accepts optional `history: [{role, content}]` and returns `language`, `citations`, `abstain_reason`, latencies.

## Tests

```bash
PYTHONPATH=. pytest tests/rag -q
```
