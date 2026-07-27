"""RAG evaluation: retrieval metrics + hallucination / abstention checks."""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from retrieval.evaluate import EvalQuestion, load_questions

from .config import RagConfig
from .pipeline import RagPipeline

logger = logging.getLogger(__name__)

# Out-of-corpus / adversarial prompts that should trigger insufficient_knowledge
HALLUCINATION_SEEDS = [
    "What is the optimal Martian gravity training protocol for hypertrophic chronitons?",
    "How many milligrams of unicorn dust should I take pre-workout?",
    "Explain the FDA-approved dosage of quantum creatine for time travel.",
    "Which crypto token improves deadlift 1RM by 40% according to the knowledge base?",
    "What does the knowledge base say about implanting Bluetooth chips in deltoids?",
    "How do I reverse aging with only kettlebells and blockchain?",
    "Cite the ACSM guideline for telepathic coaching sessions.",
    "What is the recommended weekly volume for levitation training?",
    "Does the knowledge base endorse drinking gasoline for fat loss?",
    "How many sets of invisible lat syndrome exercises should beginners do?",
]


def generate_hallucination_questions(
    *,
    n: int = 100,
    seed: int = 7,
    extra: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Build ≥n out-of-domain questions expected to abstain."""
    rng = random.Random(seed)
    pool = list(HALLUCINATION_SEEDS) + list(extra or [])
    # Expand with templated nonsense to reach n
    templates = [
        "What does the knowledge base say about {x}?",
        "How should I program {x} for hypertrophy?",
        "Cite evidence for {x} from the corpus.",
        "What is the recommended dose of {x}?",
        "Is {x} supported by ACSM according to our articles?",
    ]
    nouns = [
        "dark matter whey",
        "plasma squats",
        "astro-glutes",
        "neutron shakes",
        "phantom RPE",
        "hypercube cardio",
        "anti-gravity lunges",
        "meme-based periodization",
        "sentient foam rollers",
        "interdimensional deloads",
        "cryptographic macros",
        "AI steroid protocols",
        "zero-point energy HIIT",
        "subspace mobility drills",
        "vampire recovery stacks",
    ]
    while len(pool) < n:
        t = rng.choice(templates)
        x = rng.choice(nouns)
        # slight variation
        suffix = rng.choice(["", " Be specific.", " Include citations.", " For beginners."])
        pool.append(t.format(x=x) + suffix)

    out = []
    for i, q in enumerate(pool[:n]):
        out.append(
            {
                "id": f"hall_{i+1:04d}",
                "question": q,
                "expect_abstain": True,
                "category": "hallucination",
            }
        )
    return out


def save_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


@dataclass
class RagEvalMetrics:
    n_retrieval: int
    recall_at_5: float
    recall_at_10: float
    mrr: float
    hit_rate: float
    n_hallucination: int
    abstain_rate: float
    false_answer_rate: float
    mean_retrieval_ms: float
    mean_total_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_retrieval": self.n_retrieval,
            "recall_at_5": self.recall_at_5,
            "recall_at_10": self.recall_at_10,
            "mrr": self.mrr,
            "hit_rate": self.hit_rate,
            "n_hallucination": self.n_hallucination,
            "abstain_rate": self.abstain_rate,
            "false_answer_rate": self.false_answer_rate,
            "mean_retrieval_ms": self.mean_retrieval_ms,
            "mean_total_ms": self.mean_total_ms,
        }


def _path_match(hit_path: str, relevant_paths: list[str]) -> bool:
    hp = hit_path.replace("\\", "/")
    for rp in relevant_paths:
        r = rp.replace("\\", "/")
        if hp == r or hp.endswith(r) or r.endswith(hp):
            return True
    return False


def evaluate_retrieval(
    pipeline: RagPipeline,
    questions: list[EvalQuestion],
) -> tuple[dict[str, float], list[float]]:
    """Measure Recall@K / MRR using RAG retriever (+ optional noop rerank)."""
    recalls5: list[float] = []
    recalls10: list[float] = []
    mrrs: list[float] = []
    hits_flags: list[float] = []
    times: list[float] = []

    for q in questions:
        result = pipeline.retriever.retrieve(q.question, apply_guard=False)
        times.append(result.elapsed_ms)
        # Apply rerank for final ranking quality (usually noop in CI)
        ranked = pipeline.reranker.rerank(q.question, result.hits).hits

        def is_rel(i: int) -> bool:
            if i >= len(ranked):
                return False
            h = ranked[i]
            if q.relevant_paths and _path_match(h.citation.file_path, q.relevant_paths):
                return True
            if h.chunk and h.chunk.doc_id and h.chunk.doc_id in q.relevant_doc_ids:
                return True
            return False

        rel_flags = [is_rel(i) for i in range(len(ranked))]
        # Pad for metrics helpers that expect binary relevance list aligned to ranks
        recalls5.append(1.0 if any(rel_flags[:5]) else 0.0)
        recalls10.append(1.0 if any(rel_flags[:10]) else 0.0)
        rr = 0.0
        for i, flag in enumerate(rel_flags, start=1):
            if flag:
                rr = 1.0 / i
                break
        mrrs.append(rr)
        hits_flags.append(1.0 if any(rel_flags) else 0.0)

    metrics = {
        "recall_at_5": sum(recalls5) / len(recalls5) if recalls5 else 0.0,
        "recall_at_10": sum(recalls10) / len(recalls10) if recalls10 else 0.0,
        "mrr": sum(mrrs) / len(mrrs) if mrrs else 0.0,
        "hit_rate": sum(hits_flags) / len(hits_flags) if hits_flags else 0.0,
    }
    return metrics, times


def evaluate_hallucination(
    pipeline: RagPipeline,
    rows: list[dict[str, Any]],
) -> tuple[float, float, list[float]]:
    """Abstain rate on adversarial questions; false_answer = answered when should abstain."""
    abstain = 0
    false_answer = 0
    totals: list[float] = []
    for row in rows:
        resp = pipeline.chat(row["question"], update_history=False)
        totals.append(resp.total_ms)
        expect = bool(row.get("expect_abstain", True))
        if expect:
            if resp.insufficient_knowledge:
                abstain += 1
            else:
                false_answer += 1
        else:
            if not resp.insufficient_knowledge:
                abstain += 1  # count as correct non-abstain under "abstain_rate" only for expect
    n = len(rows) or 1
    return abstain / n, false_answer / n, totals


def write_report(path: Path, metrics: RagEvalMetrics, *, extra: dict[str, Any] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RAG Evaluation Report",
        "",
        f"- Retrieval questions: **{metrics.n_retrieval}**",
        f"- Hallucination questions: **{metrics.n_hallucination}**",
        "",
        "## Retrieval",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Recall@5 | {metrics.recall_at_5:.4f} |",
        f"| Recall@10 | {metrics.recall_at_10:.4f} |",
        f"| MRR | {metrics.mrr:.4f} |",
        f"| Hit Rate | {metrics.hit_rate:.4f} |",
        f"| Mean retrieval (ms) | {metrics.mean_retrieval_ms:.1f} |",
        "",
        "## Hallucination / abstention",
        "",
        "| Metric | Value | Target |",
        "|--------|------:|-------:|",
        f"| Abstain rate | {metrics.abstain_rate:.4f} | ≥ 0.90 |",
        f"| False answer rate | {metrics.false_answer_rate:.4f} | ≤ 0.10 |",
        f"| Mean total latency (ms) | {metrics.mean_total_ms:.1f} | — |",
        "",
    ]
    if extra:
        lines.append("## Notes")
        lines.append("")
        for k, v in extra.items():
            lines.append(f"- {k}: `{v}`")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_rag_evaluation(
    pipeline: RagPipeline,
    config: RagConfig,
    *,
    n_retrieval: int | None = None,
    n_hallucination: int = 100,
    regenerate_hallucination: bool = True,
) -> RagEvalMetrics:
    """Run retrieval + hallucination benchmarks and write evaluation/rag_report.md."""
    q_path = config.resolve(config.eval.questions_path)
    h_path = config.resolve(config.eval.hallucination_path)
    report_path = config.resolve(config.eval.report_path)

    questions = load_questions(q_path) if q_path.exists() else []
    if n_retrieval is not None:
        questions = questions[:n_retrieval]
    if len(questions) < config.eval.min_questions and q_path.exists():
        logger.warning(
            "Only %d retrieval questions (min_questions=%d)",
            len(questions),
            config.eval.min_questions,
        )

    if regenerate_hallucination or not h_path.exists():
        hall_rows = generate_hallucination_questions(n=max(n_hallucination, config.eval.min_questions))
        save_jsonl(h_path, hall_rows)
    else:
        hall_rows = load_jsonl(h_path)
        if len(hall_rows) < n_hallucination:
            hall_rows = generate_hallucination_questions(n=n_hallucination)
            save_jsonl(h_path, hall_rows)

    ret_metrics, ret_times = evaluate_retrieval(pipeline, questions)
    abstain_rate, false_rate, total_times = evaluate_hallucination(pipeline, hall_rows)

    metrics = RagEvalMetrics(
        n_retrieval=len(questions),
        recall_at_5=ret_metrics["recall_at_5"],
        recall_at_10=ret_metrics["recall_at_10"],
        mrr=ret_metrics["mrr"],
        hit_rate=ret_metrics["hit_rate"],
        n_hallucination=len(hall_rows),
        abstain_rate=abstain_rate,
        false_answer_rate=false_rate,
        mean_retrieval_ms=(sum(ret_times) / len(ret_times)) if ret_times else 0.0,
        mean_total_ms=(sum(total_times) / len(total_times)) if total_times else 0.0,
    )
    write_report(
        report_path,
        metrics,
        extra={
            "llm": pipeline.llm.name,
            "reranker": pipeline.reranker.name,
            "retrieval_mode": config.rag.retrieval_mode,
            "confidence_threshold": config.rag.confidence_threshold,
        },
    )
    logger.info("Wrote %s", report_path)
    return metrics
