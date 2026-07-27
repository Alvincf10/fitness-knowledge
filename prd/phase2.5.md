# ROLE

You are a Senior Knowledge Engineer, Information Architect, RAG Engineer, and Exercise Science Reviewer.

Your responsibility is NOT to generate new fitness knowledge.

Instead, your task is to transform the existing repository into a production-grade AI knowledge base optimized for Retrieval-Augmented Generation (RAG), semantic search, embeddings, and future reasoning engines.

Treat this repository as the primary knowledge source for an AI Personal Fitness Coach.

Never remove scientifically valid information.

Never invent information.

Never reduce evidence quality.

Only improve organization, consistency, retrieval quality, and maintainability.

---

# OBJECTIVE

Perform a complete Knowledge Optimization pass across the entire repository.

The goal is to maximize:

- Retrieval quality
- Embedding quality
- Semantic search
- Internal linking
- Knowledge consistency
- Future reasoning compatibility

No new topics should be created unless absolutely necessary.

---

# TASK 1
Repository Audit

Scan every folder.

Generate:

KNOWLEDGE_AUDIT.md

Include:

- Total files
- Total categories
- Duplicate topics
- Duplicate IDs
- Empty files
- Broken markdown
- Broken YAML
- Missing metadata
- Missing references
- Missing related articles
- Missing tags
- Naming inconsistencies
- Folder inconsistencies

Assign every issue a severity:

Critical
High
Medium
Low

---

# TASK 2
Normalize Metadata

Every markdown must contain valid YAML.

Required fields:

---
id:
title:
category:
subcategory:
description:
difficulty:
evidence_level:
last_review:
reviewed_by:
tags:
related:
aliases:
---

Automatically normalize:

- capitalization
- spacing
- date formatting
- evidence level
- tags

---

# TASK 3
Normalize Terminology

Use consistent terminology across the repository.

Examples:

Always use:

Bench Press

Never:

Benchpress
Bench press exercise
Flat bench press (unless specifically required)

Use one canonical name for every concept.

Generate:

TERMINOLOGY_STANDARD.md

containing all canonical terms.

---

# TASK 4
Internal Linking

For every article automatically populate

Related

using semantic similarity.

Include:

Exercises

Science

Nutrition

Supplements

Programming

Injuries

FAQ

Maximum:

10 related articles.

Never duplicate links.

---

# TASK 5
Alias Generation

Every article should include aliases.

Example

Bench Press

aliases:

flat bench

barbell bench

barbell chest press

benching

BP

This improves semantic retrieval.

---

# TASK 6
Knowledge Graph

Generate

knowledge-graph.json

Represent relationships.

Example

Bench Press

↓

Pectoralis Major

↓

Mechanical Tension

↓

Strength

↓

Upper Push

↓

Chest Day

Every relationship should have a type.

Examples

TRAINS

RELATED_TO

USES

PROGRESSES_TO

REGRESSES_TO

CAUSES

PREVENTS

SUPPORTS

REQUIRES

---

# TASK 7
Index Files

Generate

INDEX.md

TREE.md

TOPICS.md

EXERCISE_INDEX.md

SCIENCE_INDEX.md

SUPPLEMENT_INDEX.md

NUTRITION_INDEX.md

PROGRAM_INDEX.md

FAQ_INDEX.md

---

# TASK 8
Embedding Optimization

Rewrite headings only if necessary.

Optimize for semantic chunking.

Target chunk size:

400–800 words.

Avoid giant documents.

Split oversized articles.

Merge tiny duplicate articles.

Never lose information.

---

# TASK 9
Cross Reference Validation

Verify every related article exists.

Detect:

Broken references

Broken filenames

Incorrect relative paths

Automatically repair.

---

# TASK 10
Duplicate Detection

Find duplicate knowledge.

Examples

Bench Press Technique

Bench Press Form

Proper Bench Press

Merge duplicates.

Keep the best version.

Generate redirects where appropriate.

---

# TASK 11
Evidence Review

Check every article.

Ensure:

Reference section exists.

Evidence level is assigned.

PubMed DOI if available.

Guidelines preferred:

ACSM

NSCA

ISSN

WHO

CDC

APTA

Remove unsupported claims.

---

# TASK 12
FAQ Mapping

Every FAQ should reference at least:

1 Exercise

1 Science article

1 Programming article

1 Related FAQ

---

# TASK 13
Retrieval Optimization

Generate keywords.

Example

Bench Press

keywords:

bench

bench press

chest press

horizontal push

pectoralis

strength

powerlifting

chest workout

These keywords improve retrieval.

---

# TASK 14
Repository Score

Generate

QUALITY_REPORT.md

Evaluate

Metadata

Evidence

Internal Linking

Consistency

Naming

Chunking

Retrieval

Embedding

Knowledge Graph

References

Maintainability

Coverage

Give each category a score out of 100.

Calculate an overall repository score.

---

# TASK 15
Migration Safety

Never overwrite valid information.

Never delete references.

Never remove evidence.

When changing filenames:

Automatically update every internal reference.

---

# TASK 16
Final Deliverables

Produce:

KNOWLEDGE_AUDIT.md

QUALITY_REPORT.md

TERMINOLOGY_STANDARD.md

INDEX.md

TREE.md

TOPICS.md

knowledge-graph.json

retrieval_keywords.json

repository_statistics.json

optimization_summary.md

---

# SUCCESS CRITERIA

The repository should be:

✓ Scientifically accurate

✓ Fully indexed

✓ Internally linked

✓ Consistent

✓ Embedding-ready

✓ Retrieval-optimized

✓ Future reasoning compatible

✓ Production-ready

Do not stop until every optimization task has been completed.