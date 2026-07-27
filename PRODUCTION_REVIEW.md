# PRODUCTION_REVIEW — fit-knowledge

**Review date:** 2026-07-27  
**Reviewer role:** Senior Knowledge / RAG Production Reviewer  
**Deployment assumption:** Primary RAG corpus for an AI Personal Fitness Coach (tomorrow)  
**Scope:** Read-only review; **no repository files were modified** for this review  
**Corpus snapshot:** 1130 knowledge articles (exercises 90 · science 5 · FAQ 1000 · nutrition 20 · supplements 15)

---

## Executive verdict

**Not fully production-ready as a complete Personal Fitness Coach knowledge base.**

The repository is strong on structural hygiene (YAML presence, indexes, graph artifacts, unbroken related paths) after Phase 2.5, but it has **critical coverage holes** and **retrieval-quality risks** that will cause wrong, thin, or overconfident coach answers in day-one production.

**Ship only with hard product guardrails** (topic refusals / escalation for injuries & programming; retrieval filters for redirect FAQs; UI disclosure of coverage limits). Otherwise delay launch for a coverage + evidence hardening sprint.

| Dimension | Production readiness |
|-----------|----------------------|
| Metadata plumbing | Mostly ready |
| Indexes / graph / keywords | Artifacts present; quality uneven |
| Exercise technique (chest/back) | Usable MVP |
| Programming / periodization | **Not ready** |
| Injuries / anatomy | **Not ready** |
| FAQ corpus | Large but noisy / duplicated |
| Evidence traceability | **Weak for RAG trust** |
| Legs / shoulders / arms / core exercises | **Severely incomplete** |

---

## Issue register

Severity definitions:

- **Critical** — Likely user harm, major factual failure, or coach cannot answer core job-to-be-done  
- **High** — Frequent retrieval failure, wrong neighbors, or systemic trust/evidence problems  
- **Medium** — Degrades answer quality or maintainability; fix before scale  
- **Low** — Polish / hygiene; fix in backlog

---

### Critical

#### C1. Empty core categories: `programming/`, `injuries/`, `anatomy/`, `decision-trees/`

**Finding:** Folders exist (`.gitkeep` only) with **0 articles**. FAQ “programming” mapping uses science proxies only; **0 FAQs link to true `programming/` paths**.

**Why it fails in production:** A fitness coach’s highest-stakes queries are “how should I program this week?”, “is this pain okay?”, “which muscles am I training?”, and branching decisions. Retrieval will fall back to thin FAQs + 5 training-principle science pages — easy to overfit or hallucinate around.

**Recommended fix:**
1. Block / escalate injury and pain queries until injury articles exist.  
2. Author minimum viable hubs before launch: programming (split/volume landmarks/deload/progression), common injuries (shoulder, low back, knee, elbow — non-diagnostic), anatomy (major muscle groups).  
3. Replace FAQ programming-proxies with real programming links once hubs exist.

**Expected impact:** Large reduction in unsafe or empty coaching on programming & pain; enables Task-12 style FAQ mapping for real.

---

#### C2. Extreme exercise coverage skew (chest/back only)

**Finding:** Exercises by folder: chest **40**, back **47**, legs **3**; **empty:** shoulders, biceps, triceps, abs, glutes, calves, forearms, full-body.

**Why it fails:** Users ask about overhead press, lateral raises, curls, hip thrusts, calf work, core. Coach will retrieve chest/back analogs or nutrition/FAQ noise → **wrong exercise prescriptions**.

**Recommended fix:** Prioritize a launch pack (~40–60) covering shoulders, glutes, quads/hamstrings depth, arms, calves, core compounds/isolations; keep stubs out of retrieval until quality bar met.

**Expected impact:** Cuts the largest class of exercise-selection retrieval failures.

---

#### C3. Science corpus too thin for reasoning (5 articles, one subcategory)

**Finding:** Only `science/training-principles/*` (volume, frequency, RIR, failure, progressive overload). Empty science trees: muscle-growth, strength, fat-loss, recovery, cardio, biomechanics, warmup, injury-prevention, programming.

**Missing concepts (no dedicated science article):** periodization, RPE (FAQ-only), muscle protein synthesis, mobility, hypertrophy mechanisms beyond overload/volume, energy systems, tendinopathy load management (as science, not just FAQ boilerplate).

**Why it fails:** Embeddings will over-retrieve the same 5 pages for unrelated science questions → **false confidence** and circular citations.

**Recommended fix:** Add ~25–40 high-leverage science pages before broad launch (hypertrophy mechanisms, RPE/RIR relationship, deload, energy balance science, protein metabolism, recovery/sleep, tendon loading, warm-up). Prefer depth over FAQ volume.

**Expected impact:** Better semantic grounding; fewer “everything cites progressive overload” answers.

---

#### C4. Systematic weak / templated evidence (especially FAQs)

**Finding:**
- **0** articles with PubMed / DOI links in body.  
- **723 / 1000** FAQs share nearly identical Evidence text: *“NSCA technique standards and biomechanics principles…”* — including many nutrition/recovery FAQs where that template is **topically wrong**.  
- Example: `faq/does-muscle-turn-into-fat.md` cites NSCA technique/biomechanics for a body-composition myth.  
- `reviewed_by: phase2.5-knowledge-optimizer` on **all 1130** articles — no human scientific sign-off signal.

**Why it fails:** RAG answers may quote “NSCA/ISSN” as if specific evidence were reviewed. Product/legal/trust risk if the coach speaks with guideline authority it does not actually ground.

**Recommended fix:**
1. Retag evidence templates by topic family (hypertrophy / nutrition / supplements / pain / technique).  
2. Downgrade `evidence_level` where only boilerplate exists.  
3. Require ≥1 real citation (guideline, meta-analysis, or DOI) for grade A/B claims used in coach answers.  
4. Separate `reviewed_by` human reviewer from optimizer passes; keep optimizer in `last_optimized_by`.

**Expected impact:** Higher answer trust; fewer authoritative-sounding false attributions.

---

### High

#### H1. Near-duplicate FAQ explosion (retrieval pollution)

**Finding:** ≥16 near-duplicate cores (≥2 phrasings); 10 groups with ≥3; **40** files marked `redirects_to` but **full bodies remain indexed**. Example core `ignore-rear-delts` has 5 near-identical filenames (`should-i`, `can-i`, `is-it-okay-to`, `do-i-need-to`, `how-important-is-it-to`).

**Why it fails:** Top-k retrieval returns 4 paraphrases of one answer → wastes context window, amplifies one shallow take, confuses citation UI.

**Recommended fix:**
1. Ingest layer: **exclude** docs with `redirects_to` from embeddings (or index redirect stub only).  
2. Merge groups to one canonical FAQ; keep aliases for paraphrases.  
3. Add retrieval dedupe by canonical `id` / `redirects_to` target.

**Expected impact:** Cleaner top-k; more room for diverse evidence neighbors.

---

#### H2. Semantically weak cross-links (token overlap ≠ coaching relevance)

**Finding:** Many nutrition FAQs link to unrelated exercises (recurring `exercises/back/assisted-pull-up.md` on protein/tofu/milk FAQs). FAQ mapping rules forced “≥1 exercise” even when the question is purely dietary.

**Why it fails:** Hybrid retrievers that boost graph/`related` edges will pull **irrelevant exercise chunks** into nutrition answers.

**Recommended fix:** Make related-link rules category-aware (nutrition FAQ → nutrition/supplement/science; exercise optional). Recompute related with embedding similarity + allowlist, not forced quotas.

**Expected impact:** Large drop in off-topic context injection.

---

#### H3. No true programming knowledge; RPE/periodization under-served

**Finding:** `faq/what-is-rpe-in-lifting.md` and mesocycle/deload FAQs exist, but **no science/programming articles** for periodization, RPE, progression models, or split design. FAQ mapping claims “programming” via proxies only.

**Recommended fix:** Promote FAQ concepts into canonical science/programming pages; link FAQs upward; add aliases (`RPE`, `rate of perceived exertion`, `1-10 effort scale`).

**Expected impact:** Coach can explain effort & planning without inventing programs from FAQ fragments.

---

#### H4. Alias gaps on high-traffic nutrition/supplement pages

**Finding:** **20** articles have **empty `aliases`**, including `nutrition/protein.md`, `supplements/creatine.md`, `supplements/caffeine.md`, `supplements/bcaas.md`, and other core nutrition topics. Separately, **~499** articles have &lt;2 aliases (thin synonym coverage).

**Why it fails:** Queries like “creatine mono”, “whey iso”, “macros”, “caloric deficit” miss canonical pages more often.

**Recommended fix:** Hand-curate aliases for top 50 entities; regenerate the rest from synonym lists; never leave core pages empty.

**Expected impact:** Measurable recall lift on branded/colloquial queries.

---

#### H5. Noisy auto-aliases (junk acronyms)

**Finding:** ~91 sampled articles include low-value acronym aliases (`iifb`, `wir`, `wiam`, `df`, `cf`, `plcp`, etc.) generated from title initials.

**Why it fails:** Pollutes lexical/alias indexes; rare collisions; adds embedding noise without user intent.

**Recommended fix:** Allowlist real acronyms (RIR, RPE, RDL, EMG, ACSM, ISSN, BMI…). Drop length≤4 initials unless curated.

**Expected impact:** Cleaner keyword space; fewer bizarre matches.

---

#### H6. Evidence grade vs citation depth mismatch

**Finding:** Many FAQs marked **A/B** while Evidence is a one-line template without study-level support. 15 articles at **C** (appropriate for niche lifts/supplements) but grade A is overused relative to citation quality.

**Recommended fix:** Recalibrate grades with a rubric tied to citation specificity; auto-cap at C when only template evidence exists.

**Expected impact:** Coach hedging becomes accurate; reduces overclaim risk.

---

### Medium

#### M1. Semantic chunking: oversized flagship exercises

**Finding:** **11** articles &gt;800 words after metadata growth (e.g. barbell bench press ~912; pull-up ~890; lat pulldown ~885). Target band was 400–800.

**Recommended fix:** Split into Technique / Programming / Mistakes / Variations child pages **or** define explicit chunk boundaries (`##` sections) in the ingest pipeline without deleting content.

**Expected impact:** Better embedding locality; less diluted vectors.

---

#### M2. Short / thin descriptions (142 &lt;40 chars)

**Finding:** Many `description` fields are question restatements or truncated intros — weak for caption-style retrieval and UI snippets.

**Recommended fix:** Enforce 120–240 character descriptions that state the claim + audience + caveat.

**Expected impact:** Better hybrid search snippets and reranker features.

---

#### M3. Ambiguous / very long FAQ filenames

**Finding:** **115** FAQ stems &gt;60 characters; heavy `is-it-okay-to-` / `how-important-is-it-to-` / `do-i-need-to-` prefixing. Filenames encode speech-act, not concept.

**Recommended fix:** Canonicalize to concept slugs (`rear-delt-training-priority.md`) + store question text in `title`/`aliases`.

**Expected impact:** Easier dedupe, redirects, and human maintenance.

---

#### M4. Inconsistent terminology residue

**Finding:** Minor body issues remain (`pecs` in ≥1 article; informal `abs` in a few). `TERMINOLOGY_STANDARD.md` is large (~47KB) and includes every article title as “canonical,” diluting true controlled vocabulary.

**Recommended fix:** Keep terminology file to **controlled entities only** (~100–200). Run a lint for banned informal muscle terms.

**Expected impact:** Consistent coach phrasing; clearer synonym map.

---

#### M5. Knowledge graph / keyword artifacts are large but shallow

**Finding:** `knowledge-graph.json` ~1.9MB, mostly `RELATED_TO` from heuristic links; few typed clinical/programming edges (`CAUSES`, `PREVENTS`, `PROGRESSES_TO` largely unused). `retrieval_keywords.json` largely mirrors tokens already in titles.

**Recommended fix:** Curate graph edges for top entities; add progression/regression for exercises; treat keywords as curated query expansions, not dump of stem tokens.

**Expected impact:** Graph RAG becomes useful instead of reinforcing weak related links.

---

#### M6. `references/` stubs are thin indexes, not citable leaves

**Finding:** `references/*.md` ~80–100 words each; not wired as first-class related targets for most articles.

**Recommended fix:** Either expand into real bibliographic hubs with DOIs **or** stop implying citation completeness via References sections that only name author-years.

**Expected impact:** Clearer provenance path for answer citations.

---

#### M7. Category vocabulary inconsistency (folder vs YAML)

**Finding:** Folders use `exercises/` / `supplements/`; YAML `category` uses singular `exercise` / `supplement`. Fine if ingest normalizes — risky if filters key on raw strings.

**Recommended fix:** Document canonical category enum in STYLE_GUIDE; validate in CI.

**Expected impact:** Prevents silent filter bugs in retrieval configs.

---

### Low

#### L1. Maintenance risk: FAQ_INDEX and generated docs churn

**Finding:** `FAQ_INDEX.md` ~110KB; many generated root docs. Easy for humans to edit indexes that a next optimize pass overwrites.

**Recommended fix:** Mark generated files; generate into `generated/`; CI check “do not hand-edit.”

**Expected impact:** Fewer merge conflicts; clearer ownership.

---

#### L2. Optimizer-only review trail

**Finding:** Every article shares the same `last_review` date and optimizer `reviewed_by`.

**Recommended fix:** Add `optimization_pass` vs `scientific_review` fields; track real review dates per domain.

**Expected impact:** Auditability for medical/legal review.

---

#### L3. Minor informal terminology / style drift

**Finding:** Small counts of informal muscle slang; Phase 1 vs Phase 2 section heading variants still coexist historically in spirit (mostly normalized Related headings).

**Recommended fix:** Style lint in CI (banned terms, required H2 set per template).

**Expected impact:** Long-term consistency.

---

#### L4. Metadata field redundancy

**Finding:** Dual fields `evidence` + `evidence_level`, `updated` + `last_review` increase schema drift risk.

**Recommended fix:** Single canonical field each; keep mirrors only during migration with deprecation note.

**Expected impact:** Simpler ingest schema.

---

## Cross-cutting risk map (focus areas)

| Focus area | Worst issues | Production effect |
|------------|--------------|-------------------|
| Retrieval failures | H1, H2, C2, C3 | Wrong neighbors; duplicate FAQ spam; missing muscle groups |
| Missing concepts | C1, C3, H3 | Cannot coach programs, pain, anatomy, periodization/RPE deeply |
| Weak evidence | C4, H6 | Authoritative tone without grounding |
| Inconsistent terminology | M4, L3 | Synonym misses; uneven coach language |
| Poor semantic chunking | M1 | Diluted embeddings on flagship lifts |
| Missing aliases | H4, H5 | Colloquial query misses + acronym noise |
| Missing cross references | C1, H2, M5 | Forced/irrelevant links; empty domains |
| Weak metadata | M2, L2, L4, H6 | Thin descriptions; fake review signal |
| Ambiguous filenames | M3 | Dedupe & ops pain |
| Duplicate concepts | H1 | Context waste; answer bias |
| Future maintenance | L1, H1, M5 | Generated-doc sprawl; graph rot |

---

## Launch recommendation

### If deploying tomorrow anyway

**Must-do guardrails (same day):**
1. **Do not embed** FAQ documents with `redirects_to` (or collapse to canonical id).  
2. **Product refusals / escalation** for injury diagnosis, sharp pain, medical conditions.  
3. **Coverage disclosure** in coach UX: limited to chest/back-heavy exercises; programming & injuries incomplete.  
4. **Rerank penalty** for off-category related edges (nutrition↛random exercise).  
5. **Downgrade trust** on answers that only cite templated Evidence lines.

### Before calling the KB “production-complete”

1. Fill critical content gaps (C1–C3).  
2. Repair evidence templates & grades (C4, H6).  
3. Deduplicate FAQ index layer (H1).  
4. Recurate related links + aliases for top entities (H2, H4, H5).  
5. Re-run a scored production review; target **Critical = 0** and Coverage/Evidence both ≥90 with human sign-off.

---

## Suggested fix priority (impact × effort)

| Priority | Issues | Effort | Impact |
|---------:|--------|--------|--------|
| P0 | C1, C4 guardrails, H1 ingest filter | S–M | Prevents unsafe/noisy launch failures |
| P1 | C2 launch exercise pack, C3 science hubs | L | Makes coach job-to-be-done viable |
| P2 | H2 related recompute, H4/H5 aliases, H6 grade recalibration | M | Retrieval precision & trust |
| P3 | M1–M7, L1–L4 | S–M | Maintainability & polish |

---

## Appendix — quantitative signals used

| Signal | Value |
|--------|------:|
| Knowledge articles | 1130 |
| Science articles | 5 |
| Empty Phase-2 categories | 4 |
| Empty exercise muscle folders | 8 |
| Legs exercises | 3 |
| FAQs with identical NSCA-technique evidence template | ~723 |
| Articles with DOI/PMID in body | 0 |
| Articles missing aliases | 20 |
| Articles with &lt;2 aliases | ~499 |
| FAQ redirect markers (`redirects_to`) | 40 |
| Near-duplicate FAQ groups (≥2 phrasings) | 16 |
| Articles &gt;800 words | 11 |
| Short descriptions (&lt;40 chars) | 142 |
| Broken `related` paths | 0 |
| FAQs linking true `programming/` | 0 |
| `reviewed_by` = optimizer only | 1130 |

---

*End of production-readiness review. No files were modified except creation of this report.*
