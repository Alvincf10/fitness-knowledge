# Fitness Knowledge Base (fitness-kb)

Version: 1.3 (Phase 4.5 — production hardening)

Evidence-based fitness knowledge base in Markdown, designed for RAG and multi-agent use (OpenClaw, Cursor Agent, LangChain, LlamaIndex, and others).

## Goals

- 100% Markdown
- Evidence-based
- Easy to RAG
- Easy to update
- Framework-agnostic
- Ready for agent consumption without extra preprocessing

## Structure

```
fit-knowledge/
├── README.md
├── CONTRIBUTING.md
├── STYLE_GUIDE.md
├── CHANGELOG.md
├── metadata/
├── exercises/
├── science/
├── supplements/
├── nutrition/
├── faq/
├── templates/
├── retrieval/          # Phase 3 indexing
├── rag/                # Phase 4 RAG + /chat API
└── references/
```

## Phase 1 Corpus Targets

| Category     | Files |
|--------------|------:|
| Exercises    |    50 |
| Science      |    20 |
| Supplements  |    15 |
| Nutrition    |    20 |
| FAQ          |    30 |
| Templates    |     5 |
| References   |     3 |

## Evidence Scale

| Grade | Meaning |
|-------|---------|
| A | Strong evidence; multiple meta-analyses |
| B | Several RCTs |
| C | Limited human evidence |
| D | Expert opinion only |

## Writing Principles

- No bro science
- No clickbait
- No medical diagnosis
- No fitness-blog citations
- Prefer meta-analyses, systematic reviews, ACSM, ISSN, NSCA, and peer-reviewed journals

## Retrieval (Phase 3)

Hybrid search over the Markdown corpus (chunk → FastEmbed → FAISS + BM25 → RRF → citations).

```bash
pip install -r requirements-retrieval.txt
python3 -m retrieval build
python3 -m retrieval query "How much protein should I eat?"
python3 -m retrieval eval
```

See [`retrieval/README.md`](retrieval/README.md) and [`config/retrieval.yaml`](config/retrieval.yaml).

## RAG Chat (Phase 4 / 4.1)

Grounded answers with citations, confidence gating, and multilingual queries (Indonesian / English). KB stays English; no translation API.

```bash
pip install -r requirements-rag.txt
python3 -m retrieval build --force   # multilingual embeddings
python3 -m rag chat "Apakah kreatin aman?"
python3 -m rag serve --port 8080   # POST /chat → language + citations
python3 -m rag calibrate --no-rerank
python3 -m rag benchmark --no-rerank
# Cross-encoder (optional): ENABLE_RERANKER=true
```

See [`rag/README.md`](rag/README.md) and [`config/rag.yaml`](config/rag.yaml).

## Status

Phases 1–4.5 are in place: corpus, indexing, multilingual RAG `/chat`, and production hardening (normalize, diversity, dynamic top-k, conversation, calibration, benchmarks).
