#!/usr/bin/env python3
"""Phase 6.5 profile evaluation."""

from __future__ import annotations

import argparse
import json
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
from profile.engine import UserProfileEngine

DEFAULT_QUESTIONS = ROOT / "evaluation" / "profile_questions.json"
DEFAULT_REPORT = ROOT / "evaluation" / "profile_report.md"


@dataclass
class ProfileEvalMetrics:
    """Aggregated profile benchmark metrics."""

    profile_accuracy: float = 0.0
    conflict_resolution_accuracy: float = 0.0
    snapshot_accuracy: float = 0.0
    profile_update_latency_ms: float = 0.0
    profile_retrieval_latency_ms: float = 0.0
    total_questions: int = 0
    failures: list[dict[str, Any]] = field(default_factory=list)


def load_questions(path: Path) -> list[dict[str, Any]]:
    """Load profile benchmark dataset."""
    return json.loads(path.read_text(encoding="utf-8"))


def read_profile_value(profile: Any, field_path: str) -> Any:
    """Read a profile field by dotted path."""
    current = profile
    for part in field_path.split("."):
        current = getattr(current, part)
    if hasattr(current, "value"):
        return current.value
    return current


def evaluate_row(engine: UserProfileEngine, row: dict[str, Any]) -> dict[str, float | str]:
    """Evaluate one row."""
    user_id = row["user_id"]
    engine.memory_manager.reset_user(user_id)
    engine._profiles.pop(user_id, None)

    for message in row.get("seed_messages", []):
        engine.update_from_message(user_id, message)

    t0 = time.perf_counter()
    profile = engine.get_profile(user_id, rebuild=True)
    retrieval = engine.retrieve_with_profile_priority(user_id, row["question"])
    retrieval_ms = (time.perf_counter() - t0) * 1000.0

    expected = row["expected_value"]
    actual = read_profile_value(profile, row["expected_field"])
    profile_hit = str(expected).lower() in str(actual).lower()

    snapshot_text = retrieval["snapshot"].text.lower()
    snapshot_hit = any(token.lower() in snapshot_text for token in row.get("snapshot_tokens", [str(expected)]))

    conflict_hit = True
    if row.get("conflict_expected"):
        conflict_hit = str(row["conflict_expected"]).lower() in str(actual).lower()

    return {
        "profile_hit": 1.0 if profile_hit else 0.0,
        "snapshot_hit": 1.0 if snapshot_hit else 0.0,
        "conflict_hit": 1.0 if conflict_hit else 0.0,
        "update_latency_ms": float(row.get("last_update_latency_ms", 0.0)),
        "retrieval_latency_ms": retrieval_ms,
        "actual": str(actual),
    }


def run_evaluation(questions: list[dict[str, Any]]) -> ProfileEvalMetrics:
    """Run full profile evaluation."""
    cfg = load_memory_config(knowledge_root=ROOT)
    cfg.embedding_provider = "hash"
    cfg.db_path = str(ROOT / "data" / "profile_eval.db")
    manager = MemoryManager(cfg)
    engine = UserProfileEngine(manager)

    profile_hits: list[float] = []
    conflict_hits: list[float] = []
    snapshot_hits: list[float] = []
    update_latencies: list[float] = []
    retrieval_latencies: list[float] = []
    failures: list[dict[str, Any]] = []

    for row in questions:
        user_id = row["user_id"]
        manager.reset_user(user_id)
        engine._profiles.pop(user_id, None)

        last_latency = 0.0
        for message in row.get("seed_messages", []):
            result = engine.update_from_message(user_id, message)
            last_latency = result.latency_ms

        row["last_update_latency_ms"] = last_latency
        result = evaluate_row(engine, row)
        profile_hits.append(float(result["profile_hit"]))
        conflict_hits.append(float(result["conflict_hit"]))
        snapshot_hits.append(float(result["snapshot_hit"]))
        update_latencies.append(last_latency)
        retrieval_latencies.append(float(result["retrieval_latency_ms"]))
        if not all([result["profile_hit"], result["snapshot_hit"], result["conflict_hit"]]):
            failures.append({"id": row["id"], "actual": result["actual"]})

    return ProfileEvalMetrics(
        profile_accuracy=statistics.mean(profile_hits) if profile_hits else 0.0,
        conflict_resolution_accuracy=statistics.mean(conflict_hits) if conflict_hits else 0.0,
        snapshot_accuracy=statistics.mean(snapshot_hits) if snapshot_hits else 0.0,
        profile_update_latency_ms=statistics.mean(update_latencies) if update_latencies else 0.0,
        profile_retrieval_latency_ms=statistics.mean(retrieval_latencies) if retrieval_latencies else 0.0,
        total_questions=len(questions),
        failures=failures[:10],
    )


def render_report(metrics: ProfileEvalMetrics) -> str:
    """Render markdown report."""
    def status(ok: bool) -> str:
        return "PASS" if ok else "FAIL"

    lines = [
        "# Phase 6.5 Profile Evaluation Report",
        "",
        f"- **Questions evaluated:** {metrics.total_questions}",
        "",
        "| Metric | Result | Target | Status |",
        "|--------|--------|--------|--------|",
        f"| Profile Accuracy | {metrics.profile_accuracy:.1%} | >=98% | {status(metrics.profile_accuracy >= 0.98)} |",
        f"| Conflict Resolution Accuracy | {metrics.conflict_resolution_accuracy:.1%} | >=98% | {status(metrics.conflict_resolution_accuracy >= 0.98)} |",
        f"| Snapshot Accuracy | {metrics.snapshot_accuracy:.1%} | >=98% | {status(metrics.snapshot_accuracy >= 0.98)} |",
        f"| Profile Update Latency | {metrics.profile_update_latency_ms:.2f} ms | <5 ms | {status(metrics.profile_update_latency_ms < 5.0)} |",
        f"| Profile Retrieval Latency | {metrics.profile_retrieval_latency_ms:.2f} ms | <5 ms | {status(metrics.profile_retrieval_latency_ms < 5.0)} |",
        "",
    ]
    if metrics.failures:
        lines.extend(["## Sample Failures", ""])
        lines.extend(f"- `{item['id']}` actual=`{item['actual']}`" for item in metrics.failures)
    return "\n".join(lines) + "\n"


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Evaluate user profile engine")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    questions = load_questions(args.questions)
    if args.limit > 0:
        questions = questions[: args.limit]
    metrics = run_evaluation(questions)
    report = render_report(metrics)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
