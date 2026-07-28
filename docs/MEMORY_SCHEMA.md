# Phase 6 — Memory Schema

## SQLite Table: `memory`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment primary key |
| `user_id` | TEXT NOT NULL | Stable user identifier |
| `category` | TEXT NOT NULL | Memory category (see below) |
| `content` | TEXT NOT NULL | Human-readable fact, e.g. `goal: cutting` |
| `embedding` | BLOB NOT NULL | Packed float32 vector (`struct.pack`) |
| `importance` | REAL NOT NULL | Importance weight in [0, 1], default 0.5 |
| `created_at` | TEXT NOT NULL | ISO-8601 UTC timestamp |
| `updated_at` | TEXT NOT NULL | ISO-8601 UTC timestamp |

### Indexes

- `idx_memory_user` on `(user_id)`
- `idx_memory_user_category` on `(user_id, category)`

## Categories

| Category | Example content | Example extraction |
|----------|-----------------|-------------------|
| `goal` | `goal: cutting` | "Saya ingin cutting." |
| `experience` | `experience: beginner` | "Saya pemula." |
| `height` | `height: 175` | "Tinggi 175 cm." |
| `weight` | `weight: 82` | "Berat 82 kg." |
| `age` | `age: 28` | "Umur 28 tahun." |
| `injury` | `injury: knee` | "Cedera lutut." |
| `equipment` | `equipment: dumbbell` | "Punya dumbbell." |
| `favorite_exercise` | `favorite_exercise: bench press` | "Favorit bench press." |
| `workout_split` | `workout_split: ppl` | "Pakai push pull legs." |
| `schedule` | `schedule: morning_workout` | "Gym jam 6 pagi." |
| `supplement` | `supplement: creatine` | "Minum creatine." |
| `diet` | `diet: keto` | "Diet keto." |
| `restriction` | `restriction: dairy` | "Alergi susu." |
| `achievement` | `achievement: pr deadlift 180kg` | "PR deadlift 180 kg." |
| `session` | `session: morning_workout=True` | Short-term only (not persisted) |

## Python Models

### `ExtractedMemory`

```python
ExtractedMemory(
    category="goal",
    value="cutting",
    content="goal: cutting",
    importance=0.9,
    metadata={},
)
```

### `MemoryRecord`

Persisted row returned from storage.

### `RankedMemory`

`MemoryRecord` plus `similarity`, `recency`, `importance`, and composite `score`.

### `ConversationSummary`

| Field | Description |
|-------|-------------|
| `current_goal` | Latest goal memory |
| `current_progress` | Weight, achievements, last workout |
| `important_facts` | Priority-ordered fact list |
| `recent_changes` | Recent user turns or memory updates |

### `BuiltMemoryContext`

Rendered prompt sections:

1. Conversation Summary
2. Relevant User Memories
3. Retrieved Knowledge
4. Current Question

## Session Schema (in-memory)

`ConversationSession`:

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | str | User identifier |
| `turns` | list[SessionTurn] | Rolling conversation |
| `facts` | dict[str, str] | Short-term key-value facts |
| `metadata` | dict | Optional session metadata |

## Embedding Format

- Provider: same as KB (`hash`, `fastembed`, `sentence_transformers`, `openai`)
- Storage: `struct.pack(f"{n}f", *vector)` as BLOB
- All vectors L2-normalized before storage

## Upsert Semantics

Long-term memories upsert on `(user_id, category, content)` — duplicate facts
refresh embedding, importance, and `updated_at`.
