"""Phase 4.5 production benchmark suite."""

from __future__ import annotations

import logging
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from retrieval.evaluate import EvalQuestion, load_questions

from .config import RagConfig
from .context import Turn
from .evaluate import (
    evaluate_hallucination,
    generate_hallucination_questions,
    load_jsonl,
    save_jsonl,
)
from .language import detect_language
from .pipeline import RagPipeline

logger = logging.getLogger(__name__)

ID_PAIRS = [
    ("Apakah creatine aman?", "Is creatine safe?", "creatine"),
    ("Berapa gram protein per hari?", "Daily protein intake?", "protein"),
    ("Latihan terbaik untuk dada?", "Best chest exercise?", "chest"),
]


@dataclass
class Phase45Metrics:
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    mrr: float = 0.0
    hit_rate: float = 0.0
    citation_accuracy: float = 0.0
    false_answer_rate: float = 0.0
    abstain_rate: float = 0.0
    cross_lingual_accuracy: float = 0.0
    mean_retrieval_ms: float = 0.0
    mean_rerank_ms: float = 0.0
    mean_total_ms: float = 0.0
    p95_total_ms: float = 0.0
    followup_success_rate: float = 0.0
    n_english: int = 0
    n_indonesian: int = 0
    n_hallucination: int = 0
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items() if k != "extras"}
        d.update(self.extras)
        return d


def _pct(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    ordered = sorted(xs)
    idx = min(len(ordered) - 1, max(0, int(round((p / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def _relevant(hit_paths: list[str], hit_docs: list[str], q: EvalQuestion) -> bool:
    for p in hit_paths:
        for rp in q.relevant_paths:
            if p == rp or p.endswith(rp) or rp.endswith(p):
                return True
    return any(d in q.relevant_doc_ids for d in hit_docs)


def _run_retrieval_metrics(
    pipeline: RagPipeline,
    questions: Sequence[EvalQuestion],
) -> tuple[dict[str, float], list[float], list[float], list[float]]:
    recalls5: list[float] = []
    recalls10: list[float] = []
    mrrs: list[float] = []
    hits_flags: list[float] = []
    cite_ok: list[float] = []
    ret_ms: list[float] = []
    rerank_ms: list[float] = []
    total_ms: list[float] = []

    for q in questions:
        pipeline.reset_conversation()
        t0 = time.perf_counter()
        # Use retriever path for recall (apply_guard False) + full chat for latency
        retrieved = pipeline.retriever.retrieve(q.question, apply_guard=False, language="en")
        reranked = pipeline.reranker.rerank(q.question, retrieved.hits, top_k=10)
        ranked = reranked.hits
        elapsed = (time.perf_counter() - t0) * 1000.0
        ret_ms.append(retrieved.elapsed_ms)
        rerank_ms.append(reranked.elapsed_ms)
        total_ms.append(elapsed)

        paths = [h.citation.file_path for h in ranked]
        docs = [
            (h.chunk.doc_id if h.chunk and h.chunk.doc_id else h.chunk_id.split("#")[0])
            for h in ranked
        ]
        flags = [_relevant(paths[: i + 1], docs[: i + 1], q) for i in range(len(ranked))]
        # per-rank relevance
        rel_at = []
        for i in range(len(ranked)):
            rel_at.append(_relevant([paths[i]], [docs[i]], q))
        recalls5.append(1.0 if any(rel_at[:5]) else 0.0)
        recalls10.append(1.0 if any(rel_at[:10]) else 0.0)
        rr = 0.0
        for i, flag in enumerate(rel_at, start=1):
            if flag:
                rr = 1.0 / i
                break
        mrrs.append(rr)
        hits_flags.append(1.0 if any(rel_at) else 0.0)
        # Citation correctness: top hit path is a real file_path string (non-empty, .md)
        top = ranked[0] if ranked else None
        cite_ok.append(
            1.0
            if top and top.citation.file_path.endswith(".md") and "/" in top.citation.file_path
            else 0.0
        )

    def avg(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    metrics = {
        "recall_at_5": avg(recalls5),
        "recall_at_10": avg(recalls10),
        "mrr": avg(mrrs),
        "hit_rate": avg(hits_flags),
        "citation_accuracy": avg(cite_ok),
    }
    return metrics, ret_ms, rerank_ms, total_ms


def _cross_lingual(pipeline: RagPipeline) -> float:
    ok = 0
    for id_q, en_q, needle in ID_PAIRS:
        id_hits = pipeline.retriever.retrieve(id_q, language="id", apply_guard=False).hits
        en_hits = pipeline.retriever.retrieve(en_q, language="en", apply_guard=False).hits
        if not id_hits or not en_hits:
            continue
        if id_hits[0].citation.file_path == en_hits[0].citation.file_path:
            ok += 1
        elif needle in id_hits[0].citation.file_path.lower() and needle in en_hits[
            0
        ].citation.file_path.lower():
            ok += 1
    return ok / len(ID_PAIRS) if ID_PAIRS else 0.0


def _followup(pipeline: RagPipeline) -> float:
    """Creatine follow-up should still surface creatine sources."""
    pipeline.reset_conversation()
    first = pipeline.chat("Is creatine safe?", update_history=True)
    second = pipeline.chat("How much should I take?", update_history=True)
    if second.insufficient_knowledge:
        return 0.0
    blob = " ".join(s.file_path.lower() + " " + (s.title or "").lower() for s in second.sources)
    return 1.0 if "creatine" in blob else 0.0


def write_benchmark_report(path: Path, m: Phase45Metrics) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Phase 4.5 Production Benchmark",
        "",
        "## Summary",
        "",
        "| Metric | Value | Target |",
        "|--------|------:|-------:|",
        f"| Recall@5 | {m.recall_at_5:.4f} | ≥ 0.99 |",
        f"| Recall@10 | {m.recall_at_10:.4f} | ≥ 0.99 |",
        f"| MRR | {m.mrr:.4f} | ≥ 0.98 |",
        f"| Hit Rate | {m.hit_rate:.4f} | — |",
        f"| Citation Accuracy | {m.citation_accuracy:.4f} | = 1.00 |",
        f"| False Answer Rate | {m.false_answer_rate:.4f} | ≤ 0.05 |",
        f"| Abstain Rate | {m.abstain_rate:.4f} | ≥ 0.95 |",
        f"| Cross-language retrieval | {m.cross_lingual_accuracy:.4f} | ≥ 0.95 |",
        f"| Follow-up success | {m.followup_success_rate:.4f} | — |",
        f"| Mean retrieval (ms) | {m.mean_retrieval_ms:.1f} | < 50 |",
        f"| Mean rerank (ms) | {m.mean_rerank_ms:.1f} | — |",
        f"| Mean total retrieve+rerank (ms) | {m.mean_total_ms:.1f} | < 100 |",
        f"| P95 total (ms) | {m.p95_total_ms:.1f} | — |",
        "",
        "## Coverage",
        "",
        f"- English retrieval questions: **{m.n_english}**",
        f"- Indonesian pair checks: **{m.n_indonesian}**",
        f"- Hallucination / OOD questions: **{m.n_hallucination}**",
        "",
        "## Notes",
        "",
        "- Cross-encoder reranker latency depends on CPU/GPU; use `noop` for CI speed.",
        "- Citation accuracy checks structured English file paths (never translated).",
        "- Follow-up test: creatine → dosage enrichment via conversation context.",
        "",
    ]
    if m.extras:
        for k, v in m.extras.items():
            lines.append(f"- {k}: `{v}`")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_phase45_benchmark(
    pipeline: RagPipeline,
    config: RagConfig,
    *,
    n_retrieval: int = 100,
    n_hallucination: int = 100,
) -> Phase45Metrics:
    q_path = config.resolve(config.eval.questions_path)
    h_path = config.resolve(config.eval.hallucination_path)
    report = config.resolve(
        getattr(config.eval, "benchmark_report_path", "evaluation/benchmark_phase45.md")
    )

    questions = load_questions(q_path)[:n_retrieval] if q_path.exists() else []
    hall = load_jsonl(h_path)
    if len(hall) < n_hallucination:
        hall = generate_hallucination_questions(n=n_hallucination)
        save_jsonl(h_path, hall)
    hall = hall[:n_hallucination]

    ret_metrics, ret_ms, rerank_ms, total_ms = _run_retrieval_metrics(pipeline, questions)
    pipeline.reset_conversation()
    abstain, false_ans, _ = evaluate_hallucination(pipeline, hall)
    cross = _cross_lingual(pipeline)
    follow = _followup(pipeline)

    # Language detection spot-check
    id_ok = detect_language("Apakah kreatin aman?").code == "id"
    en_ok = detect_language("Is creatine safe?").code == "en"

    metrics = Phase45Metrics(
        recall_at_5=ret_metrics["recall_at_5"],
        recall_at_10=ret_metrics["recall_at_10"],
        mrr=ret_metrics["mrr"],
        hit_rate=ret_metrics["hit_rate"],
        citation_accuracy=ret_metrics["citation_accuracy"],
        false_answer_rate=false_ans,
        abstain_rate=abstain,
        cross_lingual_accuracy=cross,
        mean_retrieval_ms=statistics.mean(ret_ms) if ret_ms else 0.0,
        mean_rerank_ms=statistics.mean(rerank_ms) if rerank_ms else 0.0,
        mean_total_ms=statistics.mean(total_ms) if total_ms else 0.0,
        p95_total_ms=_pct(total_ms, 95),
        followup_success_rate=follow,
        n_english=len(questions),
        n_indonesian=len(ID_PAIRS),
        n_hallucination=len(hall),
        extras={
            "language_detect_id": id_ok,
            "language_detect_en": en_ok,
            "reranker": pipeline.reranker.name,
            "enable_reranker": config.rag.enable_reranker,
        },
    )
    write_benchmark_report(report, metrics)
    logger.info("Wrote %s", report)
    return metrics
