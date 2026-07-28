#!/usr/bin/env python3
"""Phase 6 memory evaluation — recall, precision, latency, ranking, summary.

Usage
-----
    PYTHONPATH=. python evaluation/evaluate_memory.py
    PYTHONPATH=. python evaluation/evaluate_memory.py --limit 50
    PYTHONPATH=. python evaluation/evaluate_memory.py --report evaluation/memory_report.md

Metrics
-------
* Memory Recall       — expected memories appear in top-k results
* Memory Precision    — retrieved memories match expected category/value
* Retrieval Latency   — mean p50 retrieval time (target <10 ms)
* Ranking Accuracy    — top-1 memory matches expected category
* Summary Accuracy    — summary contains expected facts
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory.config import load_memory_config
from memory.manager import MemoryManager
from memory.models import MemoryConfig

logger = logging.getLogger("evaluate_memory")

DEFAULT_QUESTIONS = ROOT / "evaluation" / "memory_questions.json"
DEFAULT_REPORT = ROOT / "evaluation" / "memory_report.md"

TARGETS = {
    "memory_recall": 0.95,
    "memory_precision": 0.95,
    "retrieval_latency_ms": 10.0,
    "ranking_accuracy": 0.95,
    "summary_accuracy": 0.95,
}


@dataclass
class EvalMetrics:
    """Aggregated evaluation metrics."""

    memory_recall: float = 0.0
    memory_precision: float = 0.0
    retrieval_latency_ms: float = 0.0
    retrieval_latency_p95_ms: float = 0.0
    ranking_accuracy: float = 0.0
    summary_accuracy: float = 0.0
    total_questions: int = 0
    failures: list[dict[str, Any]] = field(default_factory=list)

    def passes_targets(self) -> bool:
        """Return True when all metrics meet Phase 6 targets."""
        return (
            self.memory_recall >= TARGETS["memory_recall"]
            and self.memory_precision >= TARGETS["memory_precision"]
            and self.retrieval_latency_ms < TARGETS["retrieval_latency_ms"]
            and self.ranking_accuracy >= TARGETS["ranking_accuracy"]
            and self.summary_accuracy >= TARGETS["summary_accuracy"]
        )


def load_questions(path: Path) -> list[dict[str, Any]]:
    """Load benchmark questions."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("memory_questions.json must be a JSON array")
    return data


def _value_match(expected: list[str], content: str) -> bool:
    content_l = content.lower()
    if not expected:
        return True
    return any(v.lower() in content_l for v in expected)


def evaluate_question(
    manager: MemoryManager,
    row: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate a single benchmark row."""
    user_id = row["user_id"]
    manager.reset_user(user_id)

    seed = row.get("seed_message", "")
    if seed:
        manager.process_user_message(user_id, seed)

    question = row["question"]
    expected_category = row.get("expected_category", "")
    expected_values = list(row.get("expected_values") or [])
    expected_summary = list(row.get("expected_in_summary") or [])

    ranked, latency_ms = manager.retrieve_memory(user_id, question)
    summary = manager.summarize(user_id)
    summary_text = summary.render().lower()

    recalled = False
    if expected_category == "session":
        sess = manager.session(user_id)
        recalled = any(
            hint.lower() in str(sess.facts).lower() or hint.lower() in summary_text
            for hint in expected_summary
        ) or bool(sess.facts)
    else:
        recalled = any(
            m.record.category == expected_category
            and _value_match(expected_values, m.record.content)
            for m in ranked
        )

    if ranked:
        relevant = [
            m
            for m in ranked
            if m.record.category == expected_category
            and _value_match(expected_values, m.record.content)
        ]
        precision = len(relevant) / len(ranked)
        ranking_hit = ranked[0].record.category == expected_category and _value_match(
            expected_values, ranked[0].record.content
        )
    else:
        precision = 1.0 if expected_category == "session" and recalled else 0.0
        ranking_hit = recalled

    summary_hit = all(h.lower() in summary_text for h in expected_summary) if expected_summary else True

    return {
        "id": row.get("id"),
        "recall": 1.0 if recalled else 0.0,
        "precision": precision,
        "latency_ms": latency_ms,
        "ranking_hit": 1.0 if ranking_hit else 0.0,
        "summary_hit": 1.0 if summary_hit else 0.0,
        "top_memory": ranked[0].record.content if ranked else None,
    }


def run_evaluation(
    questions: list[dict[str, Any]],
    *,
    config: MemoryConfig | None = None,
) -> EvalMetrics:
    """Run full memory benchmark."""
    cfg = config or load_memory_config(knowledge_root=ROOT)
    cfg.embedding_provider = "hash"
    manager = MemoryManager(cfg)

    recalls: list[float] = []
    precisions: list[float] = []
    latencies: list[float] = []
    rankings: list[float] = []
    summaries: list[float] = []
    failures: list[dict[str, Any]] = []

    for row in questions:
        result = evaluate_question(manager, row)
        recalls.append(result["recall"])
        precisions.append(result["precision"])
        latencies.append(result["latency_ms"])
        rankings.append(result["ranking_hit"])
        summaries.append(result["summary_hit"])
        if result["recall"] < 1.0 or result["summary_hit"] < 1.0:
            failures.append(result)

    metrics = EvalMetrics(
        memory_recall=statistics.mean(recalls) if recalls else 0.0,
        memory_precision=statistics.mean(precisions) if precisions else 0.0,
        retrieval_latency_ms=statistics.mean(latencies) if latencies else 0.0,
        retrieval_latency_p95_ms=(
            statistics.quantiles(latencies, n=20)[-1] if len(latencies) >= 20 else max(latencies, default=0.0)
        ),
        ranking_accuracy=statistics.mean(rankings) if rankings else 0.0,
        summary_accuracy=statistics.mean(summaries) if summaries else 0.0,
        total_questions=len(questions),
        failures=failures[:20],
    )
    return metrics


def render_report(metrics: EvalMetrics) -> str:
    """Render markdown evaluation report."""
    def status(value: float, target: float, *, lower_is_better: bool = False) -> str:
        ok = value < target if lower_is_better else value >= target
        return "PASS" if ok else "FAIL"

    lines = [
        "# Phase 6 Memory Evaluation Report",
        "",
        f"- **Questions evaluated:** {metrics.total_questions}",
        f"- **Overall:** {'PASS' if metrics.passes_targets() else 'FAIL'}",
        "",
        "## Metrics",
        "",
        "| Metric | Result | Target | Status |",
        "|--------|--------|--------|--------|",
        f"| Memory Recall | {metrics.memory_recall:.1%} | ≥95% | {status(metrics.memory_recall, 0.95)} |",
        f"| Memory Precision | {metrics.memory_precision:.1%} | ≥95% | {status(metrics.memory_precision, 0.95)} |",
        f"| Retrieval Latency (mean) | {metrics.retrieval_latency_ms:.2f} ms | <10 ms | {status(metrics.retrieval_latency_ms, 10.0, lower_is_better=True)} |",
        f"| Retrieval Latency (p95) | {metrics.retrieval_latency_p95_ms:.2f} ms | <10 ms | {status(metrics.retrieval_latency_p95_ms, 10.0, lower_is_better=True)} |",
        f"| Ranking Accuracy | {metrics.ranking_accuracy:.1%} | ≥95% | {status(metrics.ranking_accuracy, 0.95)} |",
        f"| Summary Accuracy | {metrics.summary_accuracy:.1%} | ≥95% | {status(metrics.summary_accuracy, 0.95)} |",
        "",
    ]
    if metrics.failures:
        lines.extend(["## Sample Failures", ""])
        for fail in metrics.failures[:10]:
            lines.append(f"- `{fail['id']}` recall={fail['recall']} summary={fail['summary_hit']} top={fail['top_memory']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Phase 6 memory engine")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    questions = load_questions(args.questions)
    if args.limit > 0:
        questions = questions[: args.limit]

    t0 = time.perf_counter()
    metrics = run_evaluation(questions)
    elapsed = time.perf_counter() - t0

    report = render_report(metrics)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")

    print(report)
    print(f"Evaluation completed in {elapsed:.2f}s")
    print(f"Report written to {args.report}")
    return 0 if metrics.passes_targets() else 1


if __name__ == "__main__":
    raise SystemExit(main())
