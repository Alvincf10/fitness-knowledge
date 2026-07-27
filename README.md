# Fitness Knowledge Base (fitness-kb)

Version: 1.1 (Phase 3 — retrieval)

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
# recommended:
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-retrieval.txt

python3 -m retrieval build
python3 -m retrieval query "How much protein should I eat?"
python3 -m retrieval eval
# optional rerank:
python3 -m retrieval query "How much protein should I eat?" --reranker bge
```

See [`retrieval/README.md`](retrieval/README.md) and [`config/retrieval.yaml`](config/retrieval.yaml).

## Status

Knowledge corpus + Phase 3 indexing/retrieval pipeline are in place. Run `python3 -m retrieval build` after content changes.
