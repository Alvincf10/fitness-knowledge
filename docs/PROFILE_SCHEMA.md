## UserProfile Schema

Top-level object:

```python
UserProfile(
    user_id: str,
    basic_information: dict[str, ProfileAttribute],
    fitness_goal: ProfileAttribute,
    body_metrics: BodyMetrics,
    experience: ProfileAttribute,
    workout_preferences: dict[str, ProfileAttribute],
    nutrition_preferences: dict[str, ProfileAttribute],
    equipment: list[ProfileAttribute],
    injuries: list[ProfileAttribute],
    restrictions: list[ProfileAttribute],
    supplements: list[ProfileAttribute],
    schedule: ProfileAttribute,
    favorite_exercises: list[ProfileAttribute],
    disliked_exercises: list[ProfileAttribute],
    current_program: ProfileAttribute,
    last_updated: datetime,
    confidence_score: float,
    version: int,
)
```

## ProfileAttribute

Every stored attribute keeps provenance and confidence:

```python
ProfileAttribute(
    value: Any,
    confidence: float,
    source_memory_id: int | None,
    source_kind: str,
    updated_at: datetime,
    explicit: bool,
    verified: bool,
    version: int,
)
```

## Body Metrics

- `height_cm`
- `weight_kg`
- `body_fat_percent`
- `age`
- `gender`
- `activity_level`

## Supported Field Mapping

| Memory Category | Profile Field |
|---|---|
| `goal` | `fitness_goal` |
| `experience` | `experience` |
| `height` | `body_metrics.height_cm` |
| `weight` | `body_metrics.weight_kg` |
| `age` | `body_metrics.age` |
| `schedule` | `schedule`, `workout_preferences.schedule` |
| `workout_split` | `current_program`, `workout_preferences.split` |
| `diet` | `nutrition_preferences.diet` |
| `equipment` | `equipment[]` |
| `injury` | `injuries[]` |
| `restriction` | `restrictions[]` |
| `supplement` | `supplements[]` |
| `favorite_exercise` | `favorite_exercises[]` |

## Validation Rules

- `height_cm` must be between `50` and `300`
- `weight_kg` must be between `20` and `500`
- `age` must be between `10` and `120`
- `fitness_goal` must be one of:
  `cutting`, `bulking`, `maintenance`, `strength`, `hypertrophy`,
  `endurance`, `fat_loss`, `recomp`

## Export Format

`UserProfile.export_compact()` returns:

```json
{
  "goal": "cutting",
  "weight": 82,
  "height": 175,
  "experience": "intermediate",
  "schedule": "morning_workout",
  "equipment": ["dumbbell", "barbell"],
  "injury": [],
  "restrictions": ["dairy"],
  "supplements": ["creatine"],
  "current_program": "push pull legs",
  "confidence_score": 0.84,
  "version": 3
}
```

## Snapshot Format

Snapshot sections:

1. Goal
2. Experience
3. Workout
4. Gym Time
5. Weight
6. Height
7. Equipment
8. Injury
9. Restrictions
10. Current Program
