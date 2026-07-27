# QUALITY_REPORT — fit-knowledge

**Audit date:** 2026-07-27  
**Scope:** Full repository (`exercises/`, `science/`, `faq/`, `nutrition/`, `supplements/`, metadata, templates, references, Phase 2 folders)  
**Overall score:** **98.8 / 100**

---

## Scorecard

| Category | Score | Issues found (pre-fix) | Remaining (post-fix) |
|----------|------:|--------------------------:|------------------------:|
| Duplicate files | **100** | 0 | 0 |
| Duplicate IDs | **100** | 0 | 0 |
| Missing YAML | **100** | 0 required-field gaps | 0 |
| Missing References | **100** | 0 | 0 |
| Missing Related Links | **100** | 0 | 0 |
| Broken Markdown | **100** | 0 | 0 |
| Broken Internal Links | **100** | 0 / 4885 checked | 0 |
| Empty Files | **100** | 0 | 0 |
| Invalid Folder Structure | **85** | 4 Phase 2 dirs missing | Dirs created; content still empty |
| Naming Convention | **100** | 0 | 0 |
| Tag Consistency | **100** | 2 non-kebab tags | 0 |
| Evidence Level | **100** | 76 missing `evidence_level` | 0 |

---

## Corpus snapshot

| Area | Count |
|------|------:|
| Total markdown files | 1145 |
| Knowledge articles audited | 1130 |
| Exercises | 90 |
| Science | 5 |
| FAQ | 1000 |
| Nutrition | 20 |
| Supplements | 15 |
| Templates | 5 |
| Reference indexes | 3 |

### Evidence grade distribution (articles)

| Grade | Count |
|-------|------:|
| A | 256 |
| B | 859 |
| C | 15 |
| D | 0 |

---

## Findings by category

### 1. Duplicate files — 100

- No duplicate basenames across the repository knowledge tree.
- Exercise / FAQ / nutrition / supplement filenames are unique.

### 2. Duplicate IDs — 100

- All article `id` values are unique across `exercises/`, `science/`, `faq/`, `nutrition/`, `supplements/`.

### 3. Missing YAML — 100

- All knowledge articles open with valid `---` frontmatter.
- Required fields present: `id`, `title`, `category`.

### 4. Missing References — 100

- Non-FAQ articles include `## References`.
- FAQ articles include `## Evidence` (Phase 2G) or legacy `## Scientific Evidence` (Phase 1 set of 30).

### 5. Missing Related Links — 100

- Articles include `related:` in YAML and/or a `## Related` / `## Related Articles` section.

### 6. Broken Markdown — 100

- No unmatched code fences.
- No structurally empty heading bodies detected in the audit pass.

### 7. Broken Internal Links — 100

- Checked **4885** internal `.md` targets (YAML related + body bullets + markdown links).
- **0** broken after resolution against repo-relative and same-folder paths.

### 8. Empty Files — 100

- No empty or near-empty knowledge articles (`< 30` chars).

### 9. Invalid Folder Structure — 85

**Expected Phase 1 exercise folders:** all present  
`abs`, `back`, `biceps`, `calves`, `chest`, `forearms`, `full-body`, `glutes`, `legs`, `shoulders`, `triceps`

**Phase 2 top-level domains (pre-fix):** missing  
`anatomy/`, `injuries/`, `programming/`, `decision-trees/`

**Post-fix:** directories created with `.gitkeep`. They are **not yet populated** with articles (expected given Phase 2 sequencing: 2A/2G ahead of anatomy/injury/programming/decision-tree content).

**Convention note:** Repo uses `exercises/` (plural) per Phase 1 / roadmap decision, not PRD `exercise/`.

### 10. Naming Convention — 100

- Knowledge article filenames are kebab-case.
- No spaces, underscores, or uppercase stems in article paths.

### 11. Tag Consistency — 100 (after fix)

**Pre-fix:**

| File | Tag | Fix |
|------|-----|-----|
| `faq/what-should-i-do-if-my-lower-back-hurt-during-lifting.md` | `lower back` | → `lower-back` |
| `science/training-principles/reps-in-reserve.md` | `RIR` | → `rir` |

**Post-fix:** 0 non-kebab tags in article frontmatter.

### 12. Evidence Level — 100 (after fix)

**Pre-fix:** 76 articles had `evidence` but lacked `evidence_level` and/or `last_review` (mostly Phase 1 nutrition/science/supplement/legacy exercise files).

**Post-fix:**

- `evidence_level` mirrored from `evidence` where missing
- `last_review` set from `updated` (or audit date) where missing
- All article evidence grades are in `{A,B,C,D}`

---

## Automatic fixes applied

1. Normalized 2 inconsistent tags to kebab-case.
2. Added `evidence_level` to **76** articles.
3. Added `last_review` to **76** articles.
4. Created Phase 2 folders: `anatomy/`, `injuries/`, `programming/`, `decision-trees/` (with `.gitkeep`).
5. Rebuilt `metadata/exercises.json` to catalog all **90** published exercises (`published_count: 90`, `target_count: 350`).
6. Created `metadata/science.json` for the **5** published science articles (`target_count: 120`).

---

## Remaining gaps (not auto-filled as content)

These are intentional Phase 2 backlog items, not broken files:

| Gap | Impact | Recommended next phase |
|-----|--------|------------------------|
| `anatomy/` empty | No anatomy Related targets | Early anatomy stubs / Phase 2 adjacent |
| `injuries/` empty | Limited injury RAG depth beyond FAQ safety notes | Phase 2E |
| `programming/` empty | No program templates | Phase 2F |
| `decision-trees/` empty | No YAML decision routers | Phase 2H |
| Exercise library partial (90 / ~350) | Shoulders/arms/abs/etc. still sparse | Continue Phase 2A |
| Science library partial (5 / ~120) | Many science subfolders empty | Phase 2B |
| Reference indexes are stubs | Citation hub thin | Continuous enrichment (no invented DOIs) |

---

## Scoring method

- **100:** Zero defects in category after validation.
- **Folder structure 85:** Required directories now exist; Phase 2 domains lack article content yet.
- Overall = unweighted mean of the 12 category scores.

---

## Verdict

The repository is **production-usable for current corpus RAG** (exercises + FAQ-heavy) with strong structural hygiene: unique IDs/filenames, complete YAML, references/evidence sections, and valid internal links.

Highest-leverage remaining work is **content depth** (anatomy, science, programming, remaining exercise folders), not cleanup of broken files.

---

*End of QUALITY_REPORT.md*
