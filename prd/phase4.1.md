# Phase 4.1 — Multilingual Query Support

Extend the existing RAG pipeline to fully support multilingual user queries while keeping the knowledge base in English.

## Objective

Users should be able to ask questions in Indonesian, English, or other supported languages.

The knowledge base remains entirely in English.

The assistant must always answer in the same language as the user's question.

No translation API or LLM translation step may be added.

The implementation must rely on multilingual embeddings only.

---

## Requirements

### 1. Multilingual Embedding

Ensure the embedding model supports multilingual semantic search.

Recommended models (priority order):

- BAAI/bge-m3
- jina-embeddings-v4
- multilingual-e5-large

The embedding model must retrieve English documents even when the query is written in Indonesian.

Example:

Query:
"Apakah kreatin aman?"

Retrieved document:
"Creatine is considered safe..."

---

### 2. Language Detection

Implement automatic language detection before prompt generation.

Supported at minimum:

- Indonesian (id)
- English (en)

The detected language should be stored in the request context.

Example:

{
  "language": "id"
}

Language detection must be lightweight.

Recommended libraries:

- lingua
- langdetect
- fastText (optional)

---

### 3. Prompt Builder

Update prompt_builder.py.

System prompt requirements:

- The retrieved knowledge is written in English.
- Never translate citations.
- Answer ONLY using retrieved context.
- If context is insufficient, explicitly say so.
- Always respond in the user's language.
- Do not invent facts.
- Keep technical terms accurate.
- Preserve exercise names when appropriate.

Example instruction:

"The user may ask questions in any language.
The retrieved knowledge is in English.
Reason over the English context.
Respond in the same language as the user's question."

---

### 4. No Translation Layer

Do NOT:

- translate query before retrieval
- translate documents
- call Google Translate
- call Gemini for translation
- call OpenAI for translation

Retrieval must operate directly on multilingual embeddings.

---

### 5. Citation Preservation

Never translate source names.

Correct:

Source:
exercise/chest/bench_press.md

Incorrect:

Sumber:
latihan/dada/bench_press.md

File names must remain unchanged.

---

### 6. Exercise Name Policy

Common exercise names should remain in English.

Example:

Bench Press
Romanian Deadlift
Pull Up
Lat Pulldown

Do not translate them.

---

### 7. Confidence Handling

Low retrieval confidence should still return an answer in the user's language.

Example (Indonesian):

"Maaf, saya belum memiliki informasi yang cukup dalam knowledge base untuk menjawab pertanyaan tersebut dengan yakin."

Example (English):

"I don't have enough information in my knowledge base to answer that confidently."

---

### 8. API Changes

Extend POST /chat response.

Example:

{
    "answer": "...",
    "language": "id",
    "confidence": 0.94,
    "sources": [
        ...
    ]
}

---

### 9. Tests

Add multilingual retrieval tests.

Examples:

Indonesian:

- Apakah creatine aman?
- Berapa gram protein per hari?
- Latihan terbaik untuk dada?
- Cara membentuk bahu?

English:

- Is creatine safe?
- Best chest exercise?
- Daily protein intake?

The retrieved English documents should be identical regardless of query language.

---

### 10. Acceptance Criteria

- English KB remains unchanged.
- Indonesian queries retrieve correct English documents.
- No translation API is used.
- One LLM inference per request.
- Answers always follow the user's language.
- Citations remain unchanged.
- Cross-language retrieval accuracy ≥95%.
- No measurable increase in latency compared to English-only queries.

Implementation must be modular, production-ready, well-tested, and fully integrated into the existing Phase 4 RAG pipeline.
