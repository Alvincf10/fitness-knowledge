# KNOWLEDGE_AUDIT

**Date:** 2026-07-27
**Pass:** Phase 2.5 Knowledge Optimization

## Summary

- Total knowledge articles: **1130**
- Categories with content: **5**
- Empty categories: anatomy, injuries, programming, decision-trees
- Issues logged: **75** (Critical 0, High 29, Medium 46, Low 0)
- Near-duplicate FAQ groups (≥3 phrasings): **10**
- Redirects marked (content preserved): **40**
- FAQ mapping compliant: **1000/1000**

## Counts by category

| Category | Count |
|---|---:|
| exercises | 90 |
| faq | 1000 |
| nutrition | 20 |
| science | 5 |
| supplements | 15 |

## Issues

### Critical (0)

### High (29)

**empty_category** — 4
- `anatomy/`: Category folder has no articles (Phase 2 content pending)
- `injuries/`: Category folder has no articles (Phase 2 content pending)
- `programming/`: Category folder has no articles (Phase 2 content pending)
- `decision-trees/`: Category folder has no articles (Phase 2 content pending)

**faq_mapping** — 1
- `faq/`: 19 FAQs missing full mapping (exercise+science+programming-proxy+faq)

**missing_metadata** — 24
- `faq/what-is-more-important-for-strength-technique-or-ego-loading.md`: Missing id — auto-generated
- `faq/what-is-more-important-for-strength-technique-or-ego-loading.md`: Missing title — auto-generated
- `faq/what-should-i-add-first-when-i-plateau-weight-or-reps.md`: Missing id — auto-generated
- `faq/what-should-i-add-first-when-i-plateau-weight-or-reps.md`: Missing title — auto-generated
- `faq/what-is-more-important-for-strength-technique-or-ego-loading.md`: Missing required field after normalize: aliases
- `faq/what-should-i-add-first-when-i-plateau-weight-or-reps.md`: Missing required field after normalize: aliases
- `nutrition/alcohol.md`: Missing required field after normalize: aliases
- `nutrition/bulking.md`: Missing required field after normalize: aliases
- `nutrition/carbohydrates.md`: Missing required field after normalize: aliases
- `nutrition/cutting.md`: Missing required field after normalize: aliases
- `nutrition/fat.md`: Missing required field after normalize: aliases
- `nutrition/fiber.md`: Missing required field after normalize: aliases
- `nutrition/hydration.md`: Missing required field after normalize: aliases
- `nutrition/maintenance.md`: Missing required field after normalize: aliases
- `nutrition/micronutrients.md`: Missing required field after normalize: aliases
- … +9 more

### Medium (46)

**chunking_oversized** — 4
- `exercises/back/barbell-row.md`: 804 words > 800 target
- `exercises/back/lat-pulldown.md`: 818 words > 800 target
- `exercises/back/pull-up.md`: 816 words > 800 target
- `exercises/chest/barbell-bench-press.md`: 842 words > 800 target

**missing_tags** — 2
- `faq/what-is-more-important-for-strength-technique-or-ego-loading.md`: Missing tags — inferred
- `faq/what-should-i-add-first-when-i-plateau-weight-or-reps.md`: Missing tags — inferred

**near_duplicate** — 40
- `faq/can-i-chase-a-pump-after-every-compound.md`: Near-duplicate of faq/should-i-chase-a-pump-after-every-compound.md; marked redirects_to (content preserved)
- `faq/do-i-need-to-chase-a-pump-after-every-compound.md`: Near-duplicate of faq/should-i-chase-a-pump-after-every-compound.md; marked redirects_to (content preserved)
- `faq/how-important-is-it-to-chase-a-pump-after-every-compound.md`: Near-duplicate of faq/should-i-chase-a-pump-after-every-compound.md; marked redirects_to (content preserved)
- `faq/is-it-okay-to-chase-a-pump-after-every-compound.md`: Near-duplicate of faq/should-i-chase-a-pump-after-every-compound.md; marked redirects_to (content preserved)
- `faq/can-i-count-warm-up-sets-toward-weekly-volume.md`: Near-duplicate of faq/should-i-count-warm-up-sets-toward-weekly-volume.md; marked redirects_to (content preserved)
- `faq/do-i-need-to-count-warm-up-sets-toward-weekly-volume.md`: Near-duplicate of faq/should-i-count-warm-up-sets-toward-weekly-volume.md; marked redirects_to (content preserved)
- `faq/how-important-is-it-to-count-warm-up-sets-toward-weekly-volume.md`: Near-duplicate of faq/should-i-count-warm-up-sets-toward-weekly-volume.md; marked redirects_to (content preserved)
- `faq/is-it-okay-to-count-warm-up-sets-toward-weekly-volume.md`: Near-duplicate of faq/should-i-count-warm-up-sets-toward-weekly-volume.md; marked redirects_to (content preserved)
- `faq/can-i-ignore-rear-delts.md`: Near-duplicate of faq/should-i-ignore-rear-delts.md; marked redirects_to (content preserved)
- `faq/do-i-need-to-ignore-rear-delts.md`: Near-duplicate of faq/should-i-ignore-rear-delts.md; marked redirects_to (content preserved)
- `faq/how-important-is-it-to-ignore-rear-delts.md`: Near-duplicate of faq/should-i-ignore-rear-delts.md; marked redirects_to (content preserved)
- `faq/is-it-okay-to-ignore-rear-delts.md`: Near-duplicate of faq/should-i-ignore-rear-delts.md; marked redirects_to (content preserved)
- `faq/can-i-prioritize-upper-chest-work.md`: Near-duplicate of faq/should-i-prioritize-upper-chest-work.md; marked redirects_to (content preserved)
- `faq/do-i-need-to-prioritize-upper-chest-work.md`: Near-duplicate of faq/should-i-prioritize-upper-chest-work.md; marked redirects_to (content preserved)
- `faq/how-important-is-it-to-prioritize-upper-chest-work.md`: Near-duplicate of faq/should-i-prioritize-upper-chest-work.md; marked redirects_to (content preserved)
- … +25 more

### Low (0)

## Notes

- Phase 2.5 does **not** invent new programming/anatomy/injury articles; empty folders remain High-severity coverage gaps.
- FAQ “programming” mapping uses `science/training-principles/*` as proxies until Phase 2F.
- Near-duplicate FAQs were **not deleted**; `redirects_to` was added to preserve information while aiding retrieval.
- No PubMed DOIs were invented; evidence sections reference grades and position-stand families only when citations were missing.
