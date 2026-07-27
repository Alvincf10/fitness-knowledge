# ROADMAP — Phase 2 Knowledge Expansion

**Audit date:** 2026-07-27  
**Repository:** `fit-knowledge` (fitness-kb)  
**Scope:** Read-only audit. No knowledge articles generated or modified.  
**Phase 2A focus:** Exercise Library expansion (after this roadmap is approved).

---

## 1. Executive Summary

| Metric | Value |
|--------|------:|
| Knowledge markdown articles (excl. docs/templates/prd) | 79 |
| Phase 2 target articles | ~2060 |
| Gap | ~1981 |
| Empty exercise subfolders | 8 / 11 |
| Empty science subfolders | 9 / 10 |
| Phase 2 folders missing entirely | `anatomy/`, `injuries/`, `programming/`, `decision-trees/` |
| Exact duplicate filenames (knowledge corpus) | 0 |
| Near-duplicate / naming-conflict topics | Several (see §4) |

Phase 1 delivered a working MVP corpus (9 exercises, 5 science, 15 supplements, 20 nutrition, 30 FAQ). Phase 1 targets (50 / 20 / 15 / 20 / 30) were **met for supplements, nutrition, and FAQ**, but **missed for exercises (9/50) and science (5/20)**.

Phase 2 raises targets dramatically and adds four new top-level domains. **Preserve existing folder names** (`exercises/` plural, not Phase 2 PRD’s `exercise/`) unless a deliberate migration is approved.

---

## 2. Current Repository Snapshot

### 2.1 Top-level layout (as-is)

```
fit-knowledge/
├── README.md, CONTRIBUTING.md, STYLE_GUIDE.md, CHANGELOG.md
├── prd/phase1.md, prd/phase2.md
├── metadata/          (6 JSON catalogs)
├── templates/         (5 templates)
├── references/        (3 index stubs)
├── exercises/         (11 muscle folders; 9 articles)
├── science/           (10 topic folders; 5 articles)
├── nutrition/         (20 articles)
├── supplements/       (15 articles)
└── faq/               (30 articles)
```

### 2.2 Missing Phase 2 top-level folders

| Folder (Phase 2 PRD) | Status | Action |
|----------------------|--------|--------|
| `exercise/` | **Conflict** — repo uses `exercises/` | Keep `exercises/`; treat PRD name as alias |
| `anatomy/` | Missing | Create in Phase 2A-adjacent / early 2B |
| `science/` | Exists | Expand in Phase 2B |
| `nutrition/` | Exists | Expand in Phase 2C |
| `supplements/` | Exists | Expand in Phase 2D |
| `injuries/` | Missing | Create in Phase 2E |
| `programming/` | Missing (empty `science/programming/` exists) | Create top-level `programming/` in Phase 2F; keep science programming as theory |
| `faq/` | Exists | Expand in Phase 2G |
| `decision-trees/` | Missing | Create in Phase 2H |
| `references/` | Exists (stubs) | Expand continuously |

### 2.3 Counts vs targets

| Category | Existing | Phase 1 target | Phase 2 target | Gap to Phase 2 | Priority |
|----------|--------:|---------------:|---------------:|---------------:|----------|
| Exercises | 9 | 50 | 350 | 341 | **High** (Phase 2A) |
| Anatomy | 0 | — | 100 | 100 | High |
| Science | 5 | 20 | 120 | 115 | High |
| Nutrition | 20 | 20 | 120 | 100 | Medium |
| Supplements | 15 | 15 | 80 | 65 | Medium |
| Injuries | 0 | — | 60 | 60 | High |
| Programming | 0 | — | 80 | 80 | High |
| FAQ | 30 | 30 | 1000 | 970 | Medium |
| Decision Trees | 0 | — | 50 | 50 | Medium |
| **Total** | **79** | ~135 | **~2060** | **~1981** | — |

---

## 3. Structural & Template Inconsistencies

Do **not** bulk-rewrite existing articles during Phase 2A. Track these for a later consistency pass.

| Issue | Phase 1 (current) | Phase 2 PRD | Recommendation |
|-------|-------------------|-------------|----------------|
| Root exercise folder | `exercises/` | `exercise/` | **Keep `exercises/`** |
| Frontmatter date field | `updated` + `reviewed` | `last_review` | Prefer Phase 1 fields; map `last_review` ↔ `updated` |
| Evidence field | `evidence: A\|B\|C\|D` | `evidence_level` | Keep `evidence` |
| Related links | Free-text / related ids in JSON | `related:` in frontmatter | Add `related:` slugs during expansion |
| Exercise sections | Primary/Secondary Muscles, Benefits, Tempo, Variations, Science Summary | Muscles Worked (Primary/Secondary/Stabilizers), Breathing, ROM, Best Goals | Extend new files toward Phase 2 template; backfill later |
| README status line | Still says articles “not generated yet” | — | Doc drift only; fix when docs are updated (out of scope for this audit file’s content generation) |

---

## 4. Duplicate & Near-Duplicate Topics

### 4.1 Exact duplicates

No two knowledge articles share the same basename across the corpus.

### 4.2 Near-duplicates / topic overlap (intentional vs conflict)

| Pair / cluster | Type | Verdict | Action |
|----------------|------|---------|--------|
| `nutrition/carbohydrates.md` vs `supplements/carbohydrate.md` | Near-duplicate + naming clash | **Conflict** | Rename supplement to `carbohydrate-supplementation.md` (or `exogenous-carbohydrate.md`); keep nutrition plural for the macro |
| `nutrition/protein.md` vs `supplements/whey-protein.md` / `casein-protein.md` / FAQ protein articles | Layered overlap | OK | Keep; ensure Related links distinguish food protein vs supplements |
| `science/.../reps-in-reserve.md` vs `faq/what-is-rir.md` | Q&A mirror | OK | Keep; FAQ short, science deep |
| `science/.../failure-training.md` vs `faq/should-i-train-to-failure.md` | Q&A mirror | OK | Keep |
| `nutrition/intermittent-fasting.md` vs `faq/is-intermittent-fasting-better.md` | Q&A mirror | OK | Keep |
| `nutrition/calorie-deficit.md` + `cutting.md` + FAQs on fat loss | Conceptual overlap | OK | Keep; cutting = protocol, deficit = principle |
| `nutrition/calorie-surplus.md` + `bulking.md` | Conceptual overlap | OK | Keep |
| `exercises/legs/romanian-deadlift.md` (primary legs+glutes) vs empty `exercises/glutes/` | Placement ambiguity | Soft conflict | Keep RDL under `legs/`; add glute-primary variants under `glutes/` |
| Future `programming/` vs `science/programming/` | Folder collision risk | Soft conflict | Theory in `science/programming/`; programs in top-level `programming/` |

### 4.3 Metadata vs filesystem

| Catalog | Entries | Files on disk | Orphans |
|---------|--------:|--------------:|---------|
| `metadata/exercises.json` | 9 | 9 | None |
| `metadata/supplements.json` | 15 | 15 | None |
| `metadata/nutrition.json` | 20 | 20 | None |
| `metadata/faq.json` | 30 | 30 | None |
| Science | No catalog | 5 | Catalog missing — **create in Phase 2B** |
| Anatomy / injuries / programming / decision-trees | No catalogs | 0 | Create with folders |

---

## 5. Naming Inconsistencies

| Finding | Example | Severity | Fix (later) |
|---------|---------|----------|-------------|
| Singular vs plural carb files | `supplements/carbohydrate.md` vs `nutrition/carbohydrates.md` | High | Rename supplement file + metadata slug |
| Phase 2 PRD folder singular | `exercise/` vs repo `exercises/` | High (process) | Standardize docs on `exercises/` |
| Muscle folder vs primary muscle tags | RDL in `legs/` with `glutes` primary | Medium | Document routing rule: primary folder = dominant classification |
| Acronym slugs | `bcaas.md`, `hmb.md` | Low | Keep; list full name in `title` / `aliases` |
| Hyphenation aliases | `lat-pulldown` vs alias “lat pull-down” | Low | Keep slug; expand aliases |
| Frontmatter schema drift | Phase 1 vs Phase 2 field names | Medium | Single schema doc; migrate gradually |
| Empty folders without `.gitkeep` | 17 empty topic folders | Low | Optional markers; not required for generation |

All existing knowledge filenames are kebab-case (compliant). Root docs (`README.md`, etc.) correctly use SCREAMING/Title Case.

---

## 6. Category Roadmaps

---

### 6.1 Exercises — Phase 2A (**High**)

**Suggested hierarchy** (preserve existing):

```
exercises/
├── chest/
├── back/
├── shoulders/
├── legs/
├── glutes/
├── biceps/
├── triceps/
├── forearms/
├── abs/
├── calves/
└── full-body/
```

Optional later sub-tags via metadata (not folders): `compound|isolation`, `barbell|dumbbell|cable|machine|bodyweight`, `bilateral|unilateral`.

#### Existing files (9)

| Path | Status |
|------|--------|
| `exercises/chest/barbell-bench-press.md` | published |
| `exercises/chest/incline-dumbbell-press.md` | published |
| `exercises/chest/push-up.md` | published |
| `exercises/back/lat-pulldown.md` | published |
| `exercises/back/pull-up.md` | published |
| `exercises/back/barbell-row.md` | published |
| `exercises/legs/romanian-deadlift.md` | published |
| `exercises/legs/back-squat.md` | published |
| `exercises/legs/leg-press.md` | published |

#### Empty folders (must fill in 2A)

`shoulders/`, `glutes/`, `biceps/`, `triceps/`, `forearms/`, `abs/`, `calves/`, `full-body/`

#### Missing files (priority backlog toward ~350)

**Wave A1 — Complete Phase 1 gap (~41 to reach 50) — Priority: High**

*Chest (~12 more)*  
`decline-barbell-press`, `flat-dumbbell-press`, `dumbbell-fly`, `cable-fly`, `pec-deck`, `chest-dip`, `machine-chest-press`, `landmine-press`, `close-grip-push-up`, `deficit-push-up`, `smith-machine-bench-press`, `svend-press`

*Back (~15 more)*  
`chin-up`, `neutral-grip-pull-up`, `seated-cable-row`, `chest-supported-row`, `dumbbell-row`, `t-bar-row`, `pendlay-row`, `meadows-row`, `straight-arm-pulldown`, `face-pull`, `inverted-row`, `rack-pull`, `single-arm-lat-pulldown`, `machine-row`, `seal-row`

*Shoulders (folder empty — ~12)*  
`overhead-press`, `dumbbell-shoulder-press`, `arnold-press`, `lateral-raise`, `cable-lateral-raise`, `front-raise`, `rear-delt-fly`, `face-pull-shoulder` (or link to back face-pull), `upright-row`, `machine-shoulder-press`, `landmine-lateral-raise`, `bradford-press`

*Legs (~15 more)*  
`front-squat`, `goblet-squat`, `hack-squat`, `bulgarian-split-squat`, `walking-lunge`, `reverse-lunge`, `leg-extension`, `lying-leg-curl`, `seated-leg-curl`, `conventional-deadlift`, `sumo-deadlift`, `trap-bar-deadlift`, `good-morning`, `hip-thrust` (also glutes), `step-up`

*Glutes (~8)*  
`barbell-hip-thrust`, `glute-bridge`, `cable-kickback`, `banded-lateral-walk`, `frog-pump`, `single-leg-hip-thrust`, `cable-pull-through`, `45-degree-hyperextension`

*Biceps (~8)*  
`barbell-curl`, `dumbbell-curl`, `hammer-curl`, `incline-dumbbell-curl`, `preacher-curl`, `cable-curl`, `concentration-curl`, `ez-bar-curl`

*Triceps (~8)*  
`triceps-pushdown`, `skull-crusher`, `overhead-triceps-extension`, `close-grip-bench-press`, `diamond-push-up`, `kickback`, `bench-dip`, `jm-press`

*Abs / calves / forearms / full-body (starter set)*  
Abs: `plank`, `hanging-leg-raise`, `cable-crunch`, `ab-wheel`, `dead-bug`, `pallof-press`  
Calves: `standing-calf-raise`, `seated-calf-raise`, `leg-press-calf-raise`  
Forearms: `farmer-carry`, `wrist-curl`, `reverse-wrist-curl`, `plate-pinch`  
Full-body: `burpee`, `kettlebell-swing`, `thruster`, `clean`, `snatch` (power variants), `farmer-march`

**Wave A2 — Production library (~50 → ~150) — Priority: High**

Expand each muscle folder with:

- Equipment variants (barbell / DB / cable / machine / Smith / band / bodyweight)
- Unilateral versions
- Common gym staples for RAG coverage (e.g. `pec-deck`, `hack-squat`, `lat-pulldown-close-grip`, `smith-squat`)
- Olympic lift derivatives and kettlebell patterns under `full-body/`

**Wave A3 — Depth to ~350 — Priority: Medium**

- Specialty / rehab-adjacent variants (landmine, tempo, pause, deficit)
- Sport-specific transfers (sled push, prowler, med-ball throws)
- Machine brand-agnostic names only
- Avoid duplicate articles for trivial grip-width renames — use `aliases` + Variations section instead

#### Suggested per-folder targets (sum ≈ 350)

| Folder | Existing | Target | Priority |
|--------|--------:|-------:|----------|
| chest | 3 | 40 | High |
| back | 3 | 45 | High |
| shoulders | 0 | 35 | High |
| legs | 3 | 55 | High |
| glutes | 0 | 25 | High |
| biceps | 0 | 20 | Medium |
| triceps | 0 | 20 | Medium |
| forearms | 0 | 12 | Low |
| abs | 0 | 30 | Medium |
| calves | 0 | 12 | Low |
| full-body | 0 | 56 | Medium |
| **Total** | **9** | **350** | — |

#### Phase 2A generation rules

1. Do not overwrite the 9 published files unless incomplete (they are complete).
2. Update `metadata/exercises.json` as each batch is published.
3. Use Phase 2 exercise section set for **new** files; keep existing Phase 1 structure intact.
4. Every new file: YAML frontmatter, References, Related links to muscles/science/variations.
5. Generate in batches (e.g. 10–20 files), not all 341 at once.

---

### 6.2 Anatomy — Phase 2 (new) (**High**)

**Existing files:** none (folder absent)

**Suggested hierarchy:**

```
anatomy/
├── muscles/          # primary muscle articles
├── joints/
├── connective-tissue/
└── systems/          # e.g. energy-systems overview if not under science
```

#### Missing files (representative high-priority set toward ~100)

*Muscles (~70)*  
`pectoralis-major`, `pectoralis-minor`, `latissimus-dorsi`, `trapezius`, `rhomboids`, `erector-spinae`, `deltoid-anterior`, `deltoid-lateral`, `deltoid-posterior`, `rotator-cuff` (supraspinatus, infraspinatus, teres-minor, subscapularis — split or umbrella), `biceps-brachii`, `brachialis`, `triceps-brachii`, `forearm-flexors`, `forearm-extensors`, `rectus-abdominis`, `obliques`, `transversus-abdominis`, `iliopsoas`, `gluteus-maximus`, `gluteus-medius`, `gluteus-minimus`, `quadriceps` (RF, VL, VM, VI), `hamstrings` (BF, ST, SM), `adductors`, `gastrocnemius`, `soleus`, `tibialis-anterior`, …

*Joints / clinical (~20)*  
`glenohumeral-joint`, `scapulothoracic`, `elbow`, `wrist`, `lumbar-spine`, `thoracic-spine`, `cervical-spine`, `hip-joint`, `knee-joint`, `ankle-joint`

*Connective / other (~10)*  
`tendons`, `ligaments`, `fascia`, `cartilage`, `meniscus`

**Priority:** High (enables exercise ↔ anatomy linking). Create folder before or in parallel with late Phase 2A.

---

### 6.3 Science — Phase 2B (**High**)

**Suggested hierarchy** (exists):

```
science/
├── training-principles/   ← 5 files present
├── muscle-growth/         ← empty
├── strength/              ← empty
├── fat-loss/              ← empty
├── recovery/              ← empty
├── cardio/                ← empty
├── programming/           ← empty (theory only)
├── biomechanics/          ← empty
├── warmup/                ← empty
└── injury-prevention/     ← empty
```

#### Existing files (5)

- `science/training-principles/progressive-overload.md`
- `science/training-principles/training-volume.md`
- `science/training-principles/training-frequency.md`
- `science/training-principles/reps-in-reserve.md`
- `science/training-principles/failure-training.md`

#### Missing files (toward ~120) — Priority High first

*training-principles (~15 more)*  
`specificity`, `individualization`, `reversibility`, `variation`, `stimulus-recovery-adaptation`, `intensity`, `density`, `range-of-motion-training`, `tempo-and-time-under-tension`, `rest-intervals`, `exercise-order`, `periodization-overview`, `deload`, `autoregulation`, `minimum-effective-dose`

*muscle-growth (~20)*  
`muscle-hypertrophy`, `mechanical-tension`, `metabolic-stress`, `muscle-damage`, `protein-synthesis`, `satellite-cells`, `fiber-types`, `lengthened-partials`, `stretch-mediated-hypertrophy`, `mind-muscle-connection`, `blood-flow-restriction`, `eccentric-training`, `muscle-memory`, …

*strength (~15)*  
`strength-adaptation`, `neural-adaptations`, `rate-of-force-development`, `1rm-testing`, `peak-force`, `strength-hypertrophy-interference`, …

*fat-loss (~12)*  
`fat-loss-physiology`, `spot-reduction`, `neoat`, `metabolic-adaptation`, `refeed-science`, …

*recovery (~12)*  
`sleep-and-performance`, `muscle-soreness-doms`, `active-recovery`, `overreaching-vs-overtraining`, `hrv`, …

*cardio (~12)*  
`zone-2`, `vo2max`, `hiit-vs-liss`, `concurrent-training`, `epoc`, …

*programming theory (~12)*  
`linear-periodization`, `undulating-periodization`, `block-periodization`, `rpe-rir-systems`, `volume-landmarks`, …

*biomechanics (~12)*  
`moment-arms`, `sticking-points`, `spinal-loading`, `valgus-collapse`, …

*warmup (~5)*  
`general-warmup`, `specific-warmup`, `static-vs-dynamic-stretching`, …

*injury-prevention (~10)*  
`load-management`, `training-error`, `tendinopathy-load`, …

**Priority:** High for Phase 2B. Finish Phase 1 science gap (15 more) before deep expansion.

---

### 6.4 Nutrition — Phase 2C (**Medium**)

#### Existing files (20) — Phase 1 complete

`protein`, `carbohydrates`, `fat`, `fiber`, `meal-timing`, `bulking`, `cutting`, `maintenance`, `calorie-deficit`, `calorie-surplus`, `energy-balance`, `hydration`, `micronutrients`, `pre-workout-nutrition`, `post-workout-nutrition`, `intermittent-fasting`, `refeeds-and-diet-breaks`, `alcohol`, `plant-based-protein`, `body-recomposition`

#### Missing files (toward ~120) — suggested clusters

*Macros / micros depth (~25)*  
`leucine-threshold`, `protein-distribution`, `carb-cycling`, `omega-3-omega-6`, `sodium`, `potassium`, `iron`, `calcium`, `zinc`, `vitamin-c`, `b-vitamins`, `cholesterol-dietary`, …

*Special populations (~20)*  
`nutrition-for-women`, `perimenopause-nutrition`, `masters-athletes`, `adolescent-athletes`, `vegan-athlete`, `gluten-free-athlete`, …

*Strategies (~25)*  
`flexible-dieting`, `tracking-adherence`, `hunger-management`, `diet-fatigue`, `reverse-dieting`, `mini-cuts`, `contest-prep-overview` (non-medical), …

*Performance (~20)*  
`glycogen`, `intra-workout-nutrition`, `hydration-for-endurance`, `heat-nutrition`, …

*Myths / applied (~10)*  
`detoxes`, `sugar-and-fat-loss`, `late-night-eating`, …

**Suggested hierarchy:** flat `nutrition/` (current) + optional subfolders later: `macros/`, `strategies/`, `populations/`. Prefer flat until >60 files.

**Priority:** Medium (corpus already usable).

---

### 6.5 Supplements — Phase 2D (**Medium**)

#### Existing files (15) — Phase 1 complete

`creatine`, `whey-protein`, `casein-protein`, `caffeine`, `beta-alanine`, `citrulline`, `electrolytes`, `fish-oil`, `vitamin-d`, `magnesium`, `hmb`, `dietary-nitrate`, `sodium-bicarbonate`, `bcaas`, `carbohydrate`

#### Missing files (toward ~80)

**High:** `protein-powder-overview`, `essential-amino-acids`, `collagen`, `ashwagandha`, `rhodiola`, `creatine-loading` (or section in creatine — prefer FAQ/section over duplicate), `multivitamin`, `zinc-supplement`, `iron-supplement`, `probiotics`

**Medium:** `tart-cherry`, `curcumin`, `vitamin-c-supplement`, `carnitine`, `taurine`, `theanine`, `glycerol`, `citrulline-malate` (clarify vs citrulline), `betaine`, `phosphatidic-acid`

**Low / careful claims:** `testosterone-boosters` (evidence-negative article), `fat-burners`, `cla`, `raspberry-ketones`, `detox-supplements`

**Naming fix (High):** rename `carbohydrate.md` → `carbohydrate-supplementation.md`

**Priority:** Medium.

---

### 6.6 Injuries — Phase 2E (**High**, new folder)

**Existing files:** none

**Suggested hierarchy:**

```
injuries/
├── shoulder/
├── elbow/
├── spine/
├── hip/
├── knee/
├── ankle/
└── general/
```

#### Missing files (toward ~60) — High priority first

*Shoulder:* `rotator-cuff-tendinopathy`, `shoulder-impingement-overview`, `ac-joint-sprain`, `labral-irritation-overview`  
*Elbow:* `lateral-epicondylalgia`, `medial-epicondylalgia`  
*Spine:* `non-specific-low-back-pain`, `discogenic-pain-overview`, `sciatica-overview`  
*Hip:* `hip-flexor-strain`, `greater-trochanteric-pain`  
*Knee:* `patellofemoral-pain`, `patellar-tendinopathy`, `acl-return-to-training-overview`, `meniscus-overview`  
*Ankle:* `lateral-ankle-sprain`, `achilles-tendinopathy`  
*General:* `doms-vs-injury`, `tendinopathy-principles`, `when-to-refer`, `training-with-pain-guidelines`

**Writing constraint:** no diagnosis; modification + referral language only (APTA/ACSM-aligned).

**Priority:** High for coach safety RAG.

---

### 6.7 Programming — Phase 2F (**High**, new top-level folder)

**Existing files:** none at top level (`science/programming/` empty)

**Suggested hierarchy:**

```
programming/
├── splits/
├── beginner/
├── intermediate/
├── advanced/
├── fat-loss/
├── strength/
├── hypertrophy/
└── special/
```

#### Missing files (toward ~80)

*Splits:* `full-body-3x`, `upper-lower`, `push-pull-legs`, `bro-split-critique`, `body-part-split`  
*Beginner:* `beginner-full-body`, `beginner-upper-lower`, `first-12-weeks`  
*Hypertrophy:* `intermediate-ppl`, `volume-landmark-program`, `lengthened-bias-mesocycle`  
*Strength:* `starting-strength-style-overview`, `intermediate-strength-template`, `powerlifting-offseason`  
*Fat-loss:* `deficit-training-template`, `retain-muscle-cut-program`  
*Special:* `home-minimal-equipment`, `dumbbell-only`, `time-efficient-45-min`, `deload-week`, `peak-week-overview` (non-medical)

Link each program file to science articles and exercise library.

**Priority:** High (core coach output).

---

### 6.8 FAQ — Phase 2G (**Medium**)

#### Existing files (30) — Phase 1 complete

All published under `faq/` (see `metadata/faq.json`). Topics cover protein, creatine, failure, RIR, cardio, IF, recomp, sleep, women training, machines vs free weights, etc.

#### Missing files (toward ~1000)

Expand by **question families**, not random titles:

| Family | Example gaps | Priority |
|--------|--------------|----------|
| Exercise technique | “Is arched back on bench OK?”, “How deep should I squat?” | High |
| Programming | “How long should a mesocycle be?”, “Do I need a deload?” | High |
| Nutrition | “Do I need to track calories?”, “Are seed oils harmful?” | Medium |
| Supplements | “Is creatine safe long-term?”, “Can teens take creatine?” | Medium |
| Injuries / pain | “Should I train with knee pain?”, “What is a deload for tendinopathy?” | High |
| Special populations | pregnancy (referral-first), masters, youth | High (careful) |
| Myths | “Do squats ruin knees?”, “Does lifting make women bulky?” | Medium |

**Rule:** Prefer linking to canonical science/nutrition/exercise articles; FAQ stays short-answer layer.

**Priority:** Medium volume, High quality filters.

---

### 6.9 Decision Trees — Phase 2H (**Medium**, new)

**Existing files:** none

**Suggested hierarchy:**

```
decision-trees/
├── goals/
├── programming/
├── nutrition/
├── injury-routing/
└── equipment/
```

#### Missing files (toward ~50) — YAML trees per Phase 2 PRD

**High:**  
`goal-selection.yaml.md` or `goal-muscle-gain.md`, `beginner-program-selector`, `split-selector-by-days`, `surplus-vs-deficit-selector`, `pain-during-lift-router`, `home-vs-gym-equipment`

**Medium:**  
`deload-trigger`, `plateau-breaker`, `supplement-priority`, `protein-target-by-goal`

**Low:**  
Niche sport trees, contest-prep trees

**Priority:** Medium; depends on programming + injury corpora.

---

### 6.10 References, Templates, Metadata (supporting)

| Asset | Existing | Gap | Priority |
|-------|----------|-----|----------|
| `references/position-stands.md` | stub | Expand citations continuously | High |
| `references/systematic-reviews.md` | stub | Expand | High |
| `references/guidelines.md` | stub | Expand | High |
| Templates | 5 (exercise, science, supplement, nutrition, FAQ) | Add anatomy, injury, program, decision-tree, FAQ refresh for Phase 2 fields | High before 2E/2F |
| Metadata JSON | 6 catalogs | Add science, anatomy, injuries, programming, decision-trees; raise `target_count` | High |
| `muscles.json` / `equipment.json` | vocabularies only | Extend as new tags appear | Medium |

---

## 7. Phase Execution Order (confirmed)

| Phase | Domain | Start condition | Priority |
|-------|--------|-----------------|----------|
| **2A** | Exercise Library → ~350 | This roadmap accepted | **High — START NEXT** |
| 2B | Science → ~120 | 2A core compounds done OR parallel after Wave A1 | High |
| 2C | Nutrition → ~120 | After 2B core | Medium |
| 2D | Supplements → ~80 | After 2C or parallel with 2C | Medium |
| 2E | Injuries → ~60 | Templates + anatomy stubs ready | High |
| 2F | Programming → ~80 | Exercise + science volume usable | High |
| 2G | FAQ → ~1000 | Ongoing; surge after 2B–2F | Medium |
| 2H | Decision Trees → ~50 | Programming + injury routers ready | Medium |

**Immediate next action (Phase 2A):**  
Generate Wave A1 exercises (empty folders first: shoulders, glutes, arms, abs, calves, full-body; then deepen chest/back/legs), update `metadata/exercises.json`, do **not** overwrite the 9 published files.

---

## 8. Audit Checklist (completed)

- [x] Scan every folder  
- [x] Detect existing files  
- [x] Detect missing topics / folders  
- [x] Detect duplicate / near-duplicate topics  
- [x] Detect inconsistent naming  
- [x] Produce comprehensive roadmap with hierarchy + priority  

**Not done (per instructions):** generating knowledge markdown articles.

---

## 9. Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Generating 350 exercises without anatomy links | Weak RAG graph | Create anatomy stubs early |
| Overwriting Phase 1 articles with Phase 2 template | Content loss | Never overwrite complete files |
| `exercise/` vs `exercises/` rename | Broken paths / metadata | Keep `exercises/` |
| `carbohydrate` vs `carbohydrates` collision | Retrieval confusion | Rename supplement file |
| FAQ → 1000 without canonical pages | Redundant low-quality corpus | FAQ only after or with canonical article |
| Medical overreach in injury files | Safety | Referral language; no diagnosis |

---

*End of ROADMAP_PHASE2.md*
