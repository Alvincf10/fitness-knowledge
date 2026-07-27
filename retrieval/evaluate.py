"""Evaluation harness: Recall@K, MRR, Hit Rate."""

from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .chunker import load_json, parse_frontmatter, save_json
from .config import Config
from .pipeline import RetrievalPipeline

logger = logging.getLogger(__name__)


@dataclass
class EvalQuestion:
    id: str
    question: str
    relevant_doc_ids: list[str]
    relevant_paths: list[str]
    category: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "relevant_doc_ids": self.relevant_doc_ids,
            "relevant_paths": self.relevant_paths,
            "category": self.category,
        }


QUESTION_TEMPLATES: dict[str, list[str]] = {
    "exercise": [
        "How do I perform {title} correctly?",
        "What muscles does {title} work?",
        "What equipment do I need for {title}?",
        "Is {title} good for hypertrophy?",
        "Common mistakes on {title}",
    ],
    "science": [
        "What is {title}?",
        "Why does {title} matter for training?",
        "How should I apply {title}?",
        "Evidence for {title}",
    ],
    "nutrition": [
        "What should I know about {title}?",
        "How does {title} affect fat loss or muscle gain?",
        "Practical guidelines for {title}",
    ],
    "supplement": [
        "Does {title} work?",
        "How should I take {title}?",
        "Is {title} evidence-based?",
    ],
    "faq": [
        "{title}",
        "Answer this fitness question: {title}",
    ],
}


def _title_from_path(path: Path, meta: dict) -> str:
    return str(meta.get("title") or path.stem.replace("-", " ").title())


def generate_questions(config: Config, *, target: int = 300, seed: int = 42) -> list[EvalQuestion]:
    """Auto-generate ~target fitness questions grounded in corpus titles/ids."""
    rng = random.Random(seed)
    root = config.knowledge_root
    pool: list[tuple[str, Path, dict]] = []

    for dirname in config.knowledge_dirs:
        base = root / dirname
        if not base.is_dir():
            continue
        for path in base.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            meta, _ = parse_frontmatter(text)
            if meta.get("redirects_to"):
                continue
            cat = str(meta.get("category") or dirname.rstrip("s"))
            # Normalize categories
            if cat.endswith("s") and cat not in {"exercises", "supplements"}:
                pass
            pool.append((cat, path, meta))

    if not pool:
        raise RuntimeError("No documents found to generate evaluation questions")

    # Balance sampling across categories
    by_cat: dict[str, list[tuple[str, Path, dict]]] = {}
    for item in pool:
        key = item[0]
        # Map to template keys
        if key in {"exercise", "exercises"}:
            tkey = "exercise"
        elif key in {"science"}:
            tkey = "science"
        elif key in {"nutrition"}:
            tkey = "nutrition"
        elif key in {"supplement", "supplements"}:
            tkey = "supplement"
        elif key in {"faq"}:
            tkey = "faq"
        else:
            tkey = "faq"
        by_cat.setdefault(tkey, []).append((tkey, item[1], item[2]))

    questions: list[EvalQuestion] = []
    # Target mix
    quotas = {
        "exercise": int(target * 0.25),
        "science": max(15, int(target * 0.1)),
        "nutrition": int(target * 0.15),
        "supplement": int(target * 0.1),
        "faq": 0,  # fill remainder
    }
    quotas["faq"] = target - sum(quotas.values())

    qnum = 0
    for tkey, quota in quotas.items():
        items = by_cat.get(tkey) or []
        if not items:
            continue
        templates = QUESTION_TEMPLATES[tkey]
        for i in range(quota):
            _, path, meta = items[i % len(items)]
            # Prefer unique docs when possible
            if i < len(items):
                _, path, meta = items[i]
            else:
                _, path, meta = rng.choice(items)
            title = _title_from_path(path, meta)
            tmpl = templates[i % len(templates)]
            question = tmpl.format(title=title)
            rel = str(path.relative_to(root)).replace("\\", "/")
            doc_id = str(meta.get("id") or path.stem)
            qnum += 1
            questions.append(
                EvalQuestion(
                    id=f"q{qnum:04d}",
                    question=question,
                    relevant_doc_ids=[doc_id],
                    relevant_paths=[rel],
                    category=tkey,
                )
            )

    # Top up if short
    while len(questions) < target:
        tkey, path, meta = rng.choice(pool)
        if tkey in {"exercise", "exercises"}:
            tk = "exercise"
        elif tkey == "science":
            tk = "science"
        elif tkey == "nutrition":
            tk = "nutrition"
        elif tkey in {"supplement", "supplements"}:
            tk = "supplement"
        else:
            tk = "faq"
        title = _title_from_path(path, meta)
        tmpl = rng.choice(QUESTION_TEMPLATES[tk])
        qnum += 1
        questions.append(
            EvalQuestion(
                id=f"q{qnum:04d}",
                question=tmpl.format(title=title),
                relevant_doc_ids=[str(meta.get("id") or path.stem)],
                relevant_paths=[str(path.relative_to(root)).replace("\\", "/")],
                category=tk,
            )
        )

    questions = questions[:target]
    out = config.path("eval_questions")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for q in questions:
            fh.write(json.dumps(q.to_dict(), ensure_ascii=False) + "\n")
    logger.info("Wrote %d evaluation questions to %s", len(questions), out)
    return questions


def load_questions(path: Path) -> list[EvalQuestion]:
    qs: list[EvalQuestion] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            qs.append(
                EvalQuestion(
                    id=data["id"],
                    question=data["question"],
                    relevant_doc_ids=list(data.get("relevant_doc_ids") or []),
                    relevant_paths=list(data.get("relevant_paths") or []),
                    category=data.get("category"),
                )
            )
    return qs


def _hit_relevant(hit_paths: list[str], hit_doc_ids: list[str], q: EvalQuestion) -> bool:
    path_set = set(q.relevant_paths)
    id_set = set(q.relevant_doc_ids)
    for p in hit_paths:
        if p in path_set:
            return True
    for d in hit_doc_ids:
        if d in id_set:
            return True
    # Prefix / stem soft match on paths
    for p in hit_paths:
        for rp in path_set:
            if p.endswith(rp) or rp.endswith(p):
                return True
    return False


def evaluate_pipeline(
    pipeline: RetrievalPipeline,
    questions: Sequence[EvalQuestion],
    *,
    ks: tuple[int, ...] = (5, 10),
) -> dict[str, Any]:
    """Run retrieval metrics over the question set."""
    recalls = {k: [] for k in ks}
    mrrs: list[float] = []
    hits: list[float] = []

    for q in questions:
        result = pipeline.retrieve(q.question)
        ranked_paths = [h.citation.file_path for h in result.hits]
        ranked_ids = [
            (h.chunk.doc_id if h.chunk and h.chunk.doc_id else h.chunk_id.split("#")[0])
            for h in result.hits
        ]

        # MRR + hit rate @10
        rr = 0.0
        for rank, (p, d) in enumerate(zip(ranked_paths, ranked_ids), start=1):
            if _hit_relevant([p], [d], q):
                rr = 1.0 / rank
                break
        mrrs.append(rr)
        hits.append(1.0 if rr > 0 else 0.0)

        for k in ks:
            ok = _hit_relevant(ranked_paths[:k], ranked_ids[:k], q)
            recalls[k].append(1.0 if ok else 0.0)

    def avg(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    metrics = {
        "n_questions": len(questions),
        "recall@5": avg(recalls.get(5, [])),
        "recall@10": avg(recalls.get(10, [])),
        "mrr": avg(mrrs),
        "hit_rate": avg(hits),
        "embedding_provider": getattr(pipeline._embed_provider, "name", "unknown"),
        "reranker": getattr(pipeline._reranker, "name", "unknown"),
        "fusion": pipeline.config.retrieval.fusion,
    }
    return metrics


def write_report(config: Config, metrics: dict[str, Any]) -> Path:
    path = config.path("eval_report")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Retrieval Evaluation Report",
        "",
        f"- Questions: **{metrics['n_questions']}**",
        f"- Embedding provider: `{metrics.get('embedding_provider')}`",
        f"- Reranker: `{metrics.get('reranker')}`",
        f"- Fusion: `{metrics.get('fusion')}`",
        "",
        "## Metrics",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| Recall@5 | {metrics['recall@5']:.4f} |",
        f"| Recall@10 | {metrics['recall@10']:.4f} |",
        f"| MRR | {metrics['mrr']:.4f} |",
        f"| Hit Rate | {metrics['hit_rate']:.4f} |",
        "",
        "## Notes",
        "",
        "- Relevance labels are auto-derived from source document titles/ids.",
        "- Hallucination guard may zero out low-confidence hits (counted as misses).",
        "- Re-run with FastEmbed for production-representative scores if Hash was used.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote evaluation report %s", path)
    return path


def run_evaluation(
    pipeline: RetrievalPipeline,
    *,
    generate: bool = True,
    n_questions: int = 300,
) -> dict[str, Any]:
    qpath = pipeline.config.path("eval_questions")
    if generate or not qpath.exists():
        questions = generate_questions(pipeline.config, target=n_questions)
    else:
        questions = load_questions(qpath)
    metrics = evaluate_pipeline(pipeline, questions)
    write_report(pipeline.config, metrics)
    return metrics
