# Fitness Knowledge Base (fitness-kb)

Version: 1.0 (Phase 1)

## Goal

Membangun knowledge base fitness yang:

- 100% Markdown
- Evidence-based
- Mudah di-RAG
- Mudah di-update
- Tidak bergantung pada framework tertentu
- Siap dipakai oleh OpenClaw, Cursor Agent, LangChain, LlamaIndex, dsb.

---

# Folder Structure

fitness-kb/

```
fitness-kb
│
├── README.md
├── CONTRIBUTING.md
├── STYLE_GUIDE.md
├── CHANGELOG.md
│
├── metadata/
│   ├── exercises.json
│   ├── muscles.json
│   ├── equipment.json
│   ├── nutrition.json
│   ├── supplements.json
│   └── faq.json
│
├── exercises/
│   │
│   ├── chest/
│   ├── back/
│   ├── shoulders/
│   ├── legs/
│   ├── glutes/
│   ├── biceps/
│   ├── triceps/
│   ├── forearms/
│   ├── abs/
│   ├── calves/
│   └── full-body/
│
├── science/
│   ├── training-principles/
│   ├── muscle-growth/
│   ├── strength/
│   ├── fat-loss/
│   ├── recovery/
│   ├── cardio/
│   ├── programming/
│   ├── biomechanics/
│   ├── warmup/
│   └── injury-prevention/
│
├── supplements/
│
├── nutrition/
│
├── faq/
│
├── templates/
│   ├── exercise-template.md
│   ├── science-template.md
│   ├── supplement-template.md
│   ├── nutrition-template.md
│   └── faq-template.md
│
└── references/
    ├── position-stands.md
    ├── systematic-reviews.md
    └── guidelines.md
```

---

# Total Markdown

## Exercises

50 files

Contoh:

```
barbell-bench-press.md
incline-dumbbell-press.md
push-up.md
lat-pulldown.md
pull-up.md
barbell-row.md
romanian-deadlift.md
back-squat.md
leg-press.md
...
```

---

## Science

20 files

```
progressive-overload.md
training-volume.md
training-frequency.md
reps-in-reserve.md
failure-training.md
muscle-hypertrophy.md
strength-adaptation.md
protein-synthesis.md
fat-loss.md
recovery.md
...
```

---

## Supplements

15 files

```
creatine.md
whey-protein.md
caffeine.md
beta-alanine.md
citrulline.md
electrolytes.md
fish-oil.md
vitamin-d.md
magnesium.md
...
```

---

## Nutrition

20 files

```
protein.md
carbohydrates.md
fat.md
meal-timing.md
bulking.md
cutting.md
maintenance.md
calorie-deficit.md
calorie-surplus.md
fiber.md
...
```

---

## FAQ

30 files

```
best-time-to-workout.md
should-i-train-to-failure.md
can-i-build-muscle-at-home.md
is-cardio-bad.md
how-much-protein.md
do-i-need-creatine.md
...
```

---

# Metadata

Setiap artikel mempunyai metadata YAML.

Contoh:

```yaml
---
id: exercise_barbell_bench_press

title: Barbell Bench Press

category: exercise

muscle_primary:
  - chest

muscle_secondary:
  - triceps
  - front-delts

equipment:
  - barbell

difficulty: intermediate

movement:
  - push

plane:
  - horizontal

goal:
  - hypertrophy
  - strength

aliases:
  - bench press

updated: 2026-07-27

reviewed: true

evidence: A
---
```

---

# Exercise Format

Setiap exercise WAJIB mengikuti struktur berikut.

```
Title

Overview

Primary Muscles

Secondary Muscles

Equipment

Difficulty

Benefits

Execution

Common Mistakes

Coaching Cues

Programming

Sets

Reps

Tempo

Rest Time

Variations

Regression

Progression

Contraindications

Science Summary

Evidence

References
```

---

# Science Format

```
Title

Definition

Why It Matters

Mechanism

Scientific Consensus

Practical Recommendation

Misconceptions

Key Takeaways

References
```

---

# Supplement Format

```
Overview

What It Is

Benefits

Who Should Take It

Recommended Dose

Timing

Side Effects

Interactions

Evidence Summary

References
```

---

# Nutrition Format

```
Overview

Definition

Daily Recommendation

Benefits

Common Mistakes

Example Foods

Practical Tips

Evidence Summary

References
```

---

# FAQ Format

```
Question

Short Answer

Detailed Explanation

Scientific Evidence

Practical Advice

Related Articles
```

---

# Evidence Scale

Semua artikel harus memiliki rating.

```
A

Strong evidence

Multiple meta-analysis

B

Several RCT

C

Limited human evidence

D

Expert opinion only
```

---

# Citation Format

Gunakan APA sederhana.

Contoh:

```
Schoenfeld BJ (2017)

Morton RW (2018)

ACSM Position Stand (2022)

ISSN Position Stand

NSCA Essentials
```

---

# Writing Rules

Agent wajib mengikuti:

- Tidak menggunakan bro science
- Tidak clickbait
- Tidak memberikan diagnosis medis
- Tidak mengutip blog fitness
- Prioritas meta-analysis
- Prioritas systematic review
- Prioritas ACSM
- Prioritas ISSN
- Prioritas NSCA
- Prioritas peer-reviewed journal

---

# Style Guide

- Bahasa Inggris
- Ringkas
- Evidence-first
- Bullet seperlunya
- Tidak menggunakan opini pribadi
- Selalu menjelaskan berdasarkan penelitian

---

# Cross Linking

Contoh:

```
Related

- Progressive Overload

- Training Volume

- Chest Hypertrophy

- Incline Bench Press
```

---

# Tags

Contoh:

```
strength

hypertrophy

beginner

intermediate

advanced

push

pull

compound

isolation

machine

free-weight

bodyweight
```

---

# Phase 1 Deliverables

| Category | Files |
|-----------|------:|
| Exercises | 50 |
| Science | 20 |
| Supplements | 15 |
| Nutrition | 20 |
| FAQ | 30 |
| Templates | 5 |
| References | 3 |

**Total:** ±143 Markdown files

---

# Acceptance Criteria

Knowledge base dianggap selesai apabila:

- Semua Markdown tervalidasi.
- Semua memiliki YAML metadata.
- Semua memiliki referensi ilmiah.
- Tidak ada placeholder.
- Seluruh artikel saling terhubung melalui Related Articles.
- Konsisten mengikuti template.
- Siap digunakan sebagai RAG corpus tanpa preprocessing tambahan.