"""Confidence threshold calibration (Phase 4.5 Task 2)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from retrieval.evaluate import EvalQuestion, load_questions

from .config import RagConfig
from .evaluate import evaluate_hallucination, generate_hallucination_questions, load_jsonl, save_jsonl
from .pipeline import RagPipeline

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]


@dataclass
class ThresholdMetrics:
    threshold: float
    recall: float
    precision: float
    abstain_rate: float
    false_answer_rate: float
    f1: float
    n_retrieval: int
    n_hallucination: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold": self.threshold,
            "recall": self.recall,
            "precision": self.precision,
            "abstain_rate": self.abstain_rate,
            "false_answer_rate": self.false_answer_rate,
            "f1": self.f1,
            "n_retrieval": self.n_retrieval,
            "n_hallucination": self.n_hallucination,
        }


def _path_match(hit_path: str, relevant_paths: list[str]) -> bool:
    hp = hit_path.replace("\\", "/")
    for rp in relevant_paths:
        r = rp.replace("\\", "/")
        if hp == r or hp.endswith(r) or r.endswith(hp):
            return True
    return False


def _eval_at_threshold(
    pipeline: RagPipeline,
    questions: Sequence[EvalQuestion],
    hall_rows: list[dict[str, Any]],
    threshold: float,
) -> ThresholdMetrics:
    """Temporarily set fusion confidence threshold and measure metrics."""
    original = pipeline.config.rag.confidence_threshold
    pipeline.config.rag.confidence_threshold = threshold
    pipeline.config.retrieval.retrieval.confidence_threshold = threshold

    # Retrieval: treat hit as success if any final source matches label when not abstaining
    tp = fp = fn = 0
    for q in questions:
        resp = pipeline.chat(q.question, update_history=False)
        if resp.insufficient_knowledge:
            fn += 1
            continue
        paths = [s.file_path for s in resp.sources]
        ok = any(_path_match(p, q.relevant_paths) for p in paths)
        if not ok and q.relevant_doc_ids:
            for s in resp.sources:
                # chunk_id prefix often equals doc_id
                doc = s.chunk_id.split("#")[0]
                if doc in q.relevant_doc_ids:
                    ok = True
                    break
        if ok:
            tp += 1
        else:
            fp += 1

    recall = tp / (tp + fn) if (tp + fn) else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    abstain_rate, false_rate, _ = evaluate_hallucination(pipeline, hall_rows)

    pipeline.config.rag.confidence_threshold = original
    pipeline.config.retrieval.retrieval.confidence_threshold = original

    return ThresholdMetrics(
        threshold=threshold,
        recall=recall,
        precision=precision,
        abstain_rate=abstain_rate,
        false_answer_rate=false_rate,
        f1=f1,
        n_retrieval=len(questions),
        n_hallucination=len(hall_rows),
    )


def recommend_threshold(rows: Sequence[ThresholdMetrics]) -> ThresholdMetrics:
    """Pick threshold maximizing F1 with abstain≥0.90 and false_answer≤0.10 when possible."""
    eligible = [r for r in rows if r.abstain_rate >= 0.90 and r.false_answer_rate <= 0.10]
    pool = eligible or list(rows)
    # Prefer higher F1, then higher abstain, then higher recall
    return max(pool, key=lambda r: (r.f1, r.abstain_rate, r.recall, -r.false_answer_rate))


def write_confidence_report(
    path: Path,
    rows: Sequence[ThresholdMetrics],
    recommended: ThresholdMetrics,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Confidence Calibration Report",
        "",
        "Automatic sweep of fusion confidence thresholds for the RAG guard.",
        "",
        f"**Recommended threshold:** `{recommended.threshold:.2f}` "
        f"(F1={recommended.f1:.4f}, Recall={recommended.recall:.4f}, "
        f"Abstain={recommended.abstain_rate:.4f}, FalseAnswer={recommended.false_answer_rate:.4f})",
        "",
        "| Threshold | Recall | Precision | F1 | Abstain | False Answer |",
        "|----------:|-------:|----------:|---:|--------:|-------------:|",
    ]
    for r in rows:
        mark = " ←" if r.threshold == recommended.threshold else ""
        lines.append(
            f"| {r.threshold:.2f}{mark} | {r.recall:.4f} | {r.precision:.4f} | "
            f"{r.f1:.4f} | {r.abstain_rate:.4f} | {r.false_answer_rate:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Selection policy",
            "",
            "1. Prefer thresholds with Abstain Rate ≥ 0.90 and False Answer Rate ≤ 0.10.",
            "2. Among eligible (or all, if none), maximize F1, then abstain, then recall.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_confidence_calibration(
    pipeline: RagPipeline,
    config: RagConfig,
    *,
    thresholds: Sequence[float] | None = None,
    n_retrieval: int = 100,
    n_hallucination: int = 100,
) -> tuple[list[ThresholdMetrics], ThresholdMetrics]:
    """Sweep thresholds and write evaluation/confidence_report.md."""
    q_path = config.resolve(config.eval.questions_path)
    h_path = config.resolve(config.eval.hallucination_path)
    report_path = config.resolve(
        getattr(config.eval, "confidence_report_path", "evaluation/confidence_report.md")
    )

    questions = load_questions(q_path)[:n_retrieval] if q_path.exists() else []
    hall_rows = load_jsonl(h_path)
    if len(hall_rows) < n_hallucination:
        hall_rows = generate_hallucination_questions(n=n_hallucination)
        save_jsonl(h_path, hall_rows)
    else:
        hall_rows = hall_rows[:n_hallucination]

    rows: list[ThresholdMetrics] = []
    for t in thresholds or DEFAULT_THRESHOLDS:
        logger.info("Calibrating threshold=%.2f", t)
        # Avoid accumulating conversation state across questions
        pipeline.reset_conversation()
        rows.append(_eval_at_threshold(pipeline, questions, hall_rows, t))

    recommended = recommend_threshold(rows)
    write_confidence_report(report_path, rows, recommended)
    logger.info("Wrote %s (recommended=%.2f)", report_path, recommended.threshold)
    return rows, recommended
