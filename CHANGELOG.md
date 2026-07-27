# Changelog

All notable changes to this knowledge base are documented in this file.

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
