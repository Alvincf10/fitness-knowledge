# Changelog

All notable changes to this knowledge base are documented in this file.

## [1.3.0] - 2026-07-28

### Added

- Phase 4.5 production hardening:
  - Cross-encoder reranker path (`BAAI/bge-reranker-v2-m3` preferred, GPU/CPU, batch, latency logs; default noop until enabled)
  - Confidence calibration (`python3 -m rag calibrate` → `evaluation/confidence_report.md`)
  - Query normalization + extendable `config/aliases.yaml`
  - Conversation context enrichment for follow-ups
  - Dynamic Top-K by confidence bands
  - Source diversity (max chunks/doc, section + Jaccard)
  - Structured citations `{title, file, section, confidence}`
  - JSON observability traces (`rag.observability`)
  - Production benchmark (`python3 -m rag benchmark` → `evaluation/benchmark_phase45.md`)
- Feature flags in `config/rag.yaml` / env: `ENABLE_RERANKER`, `ENABLE_QUERY_NORMALIZATION`, `ENABLE_DYNAMIC_TOPK`, `ENABLE_SOURCE_DIVERSITY`, etc.
- Unit tests in `tests/rag/test_phase45.py`

### Changed

- Multilingual embedder default: `paraphrase-multilingual-MiniLM-L12-v2` (rebuild required)
- Recommended fusion confidence threshold from calibration: `0.01`

## [1.2.1] - 2026-07-28

### Added

- Phase 4.1 multilingual query support: lightweight language detection (`id`/`en`), localized abstain messages, language-aware prompts
- `POST /chat` response field `language`
- Multilingual embedding defaults: `intfloat/multilingual-e5-large` (FastEmbed); optional `BAAI/bge-m3` via `sentence_transformers`
- Non-English queries use FAISS-only retrieval (no query translation; BM25 stays English)
- Grounding lexicon maps Indonesian fitness terms → English for confidence checks only
- Tests in `tests/rag/test_multilingual.py` (cross-lingual retrieval parity)

### Changed

- Prompt builder instructs the LLM to reason over English context and answer in the user's language; citation paths and exercise names stay English

### Notes

- Rebuild indexes after upgrading embeddings: `python3 -m retrieval build --force`
- No translation API / LLM translation step is used

## [1.2.0] - 2026-07-28

### Added

- Phase 4 RAG pipeline (`rag/`): retriever, BGE/noop reranker wrapper, hallucination-resistant prompt builder, structured citations, LLM backends (`extractive` / `openai` / `mock`), and end-to-end `RagPipeline`
- FastAPI `POST /chat` with answer, sources, confidence, retrieval/rerank/total latency
- Confidence gating via fusion score + semantic floor + query–context grounding overlap
- Config `config/rag.yaml` with `RAG_*` / `OPENAI_*` environment overrides
- Automated RAG eval: retrieval metrics + ≥100 hallucination/abstention questions (`python3 -m rag eval`)
- Unit tests under `tests/rag/`

### Notes

- Default LLM is extractive (offline). Set `RAG_LLM_PROVIDER=openai` + `OPENAI_API_KEY` for chat completions.
- Prefer `pip install -r requirements-rag.txt` and existing Phase 3 indexes (`python3 -m retrieval build`).

## [1.1.1] - 2026-07-27

### Changed

- Section-based chunker v2: H2-rooted sections, merge small subsections, short docs → single chunk, title/category prefix; auto-invalidates incremental cache via `chunker_version`
- Hybrid retrieval adds title/slug boost before guard/rerank
- Optional BGE/Jina reranker via config/CLI (`noop` default for CPU speed; `bge` / `jina` when `sentence-transformers` installed)
- Re-benchmark: Recall@10 = 1.00, MRR ≈ 0.97 (300 questions, FastEmbed)

## [1.1.0] - 2026-07-27

### Added

- Phase 3 retrieval engine (`retrieval/`): Markdown chunker, FastEmbed/OpenAI/hash embeddings, FAISS + BM25 indexes, hybrid RRF retrieval, query expansion, citation payloads, hallucination guard, and optional BGE/Jina rerankers
- Config-driven settings in `config/retrieval.yaml`
- CLI: `python3 -m retrieval build|query|eval`
- Evaluation set (`evaluation/questions.jsonl`, ~300 Qs) and `evaluation/report.md`
- Unit tests under `tests/retrieval/`
- `requirements-retrieval.txt` and `retrieval/README.md`

## [1.0.7] - 2026-07-27

### Added

- All 30 FAQ articles under `faq/` with Related Article links
- Expanded `metadata/faq.json` to full published catalog

## [1.0.6] - 2026-07-27

### Added

- All 20 nutrition articles under `nutrition/`
- Expanded `metadata/nutrition.json` to full published catalog

## [1.0.5] - 2026-07-27

### Added

- All 15 supplement articles under `supplements/`
- Expanded `metadata/supplements.json` to full published catalog

## [1.0.4] - 2026-07-27

### Added

- Science training-principles: `progressive-overload.md`, `training-volume.md`, `training-frequency.md`, `reps-in-reserve.md`, `failure-training.md`

## [1.0.3] - 2026-07-27

### Added

- Legs exercises: `romanian-deadlift.md`, `back-squat.md`, `leg-press.md`

### Changed

- Updated `metadata/exercises.json` legs entries to `published` with evidence grades

## [1.0.2] - 2026-07-27

### Added

- Back exercises: `lat-pulldown.md`, `pull-up.md`, `barbell-row.md`

### Changed

- Updated `metadata/exercises.json` back entries to `published` with evidence grades

## [1.0.1] - 2026-07-27

### Added

- Chest exercises: `barbell-bench-press.md`, `incline-dumbbell-press.md`, `push-up.md`

### Changed

- Updated `metadata/exercises.json` chest entries to `published` with evidence grades

## [1.0.0-scaffold] - 2026-07-27

### Added

- Full folder structure for exercises, science, supplements, nutrition, FAQ, templates, metadata, and references
- Root docs: `README.md`, `CONTRIBUTING.md`, `STYLE_GUIDE.md`, `CHANGELOG.md`
- Templates for exercise, science, supplement, nutrition, and FAQ articles
- Metadata JSON catalogs: exercises, muscles, equipment, nutrition, supplements, FAQ
- Reference index stubs: position stands, systematic reviews, guidelines

### Notes

- Knowledge articles are intentionally not generated in this scaffold phase
