# Confidence Calibration Report

Automatic sweep of fusion confidence thresholds for the RAG guard.

**Recommended threshold:** `0.01` (F1=0.9474, Recall=0.9000, Abstain=1.0000, FalseAnswer=0.0000)

| Threshold | Recall | Precision | F1 | Abstain | False Answer |
|----------:|-------:|----------:|---:|--------:|-------------:|
| 0.01 ← | 0.9000 | 1.0000 | 0.9474 | 1.0000 | 0.0000 |
| 0.02 | 0.9000 | 1.0000 | 0.9474 | 1.0000 | 0.0000 |
| 0.03 | 0.9000 | 1.0000 | 0.9474 | 1.0000 | 0.0000 |
| 0.04 | 0.9000 | 1.0000 | 0.9474 | 1.0000 | 0.0000 |
| 0.05 | 0.9000 | 1.0000 | 0.9474 | 1.0000 | 0.0000 |
| 0.06 | 0.9000 | 1.0000 | 0.9474 | 1.0000 | 0.0000 |
| 0.07 | 0.6875 | 1.0000 | 0.8148 | 1.0000 | 0.0000 |
| 0.08 | 0.3250 | 1.0000 | 0.4906 | 1.0000 | 0.0000 |
| 0.09 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| 0.10 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |

## Selection policy

1. Prefer thresholds with Abstain Rate ≥ 0.90 and False Answer Rate ≤ 0.10.
2. Among eligible (or all, if none), maximize F1, then abstain, then recall.
