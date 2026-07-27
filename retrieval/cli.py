"""CLI for build / query / eval."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .config import load_config, setup_logging
from .evaluate import run_evaluation
from .pipeline import RetrievalPipeline

logger = logging.getLogger(__name__)


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        default=None,
        help="Path to retrieval.yaml (default: config/retrieval.yaml)",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Knowledge root directory (default: fit-knowledge/)",
    )


def cmd_build(args: argparse.Namespace) -> int:
    cfg = load_config(args.config, args.root)
    setup_logging(cfg.log_level)
    if args.provider:
        cfg.embedding.provider = args.provider
    if args.embed_model:
        cfg.embedding.model = args.embed_model
    if getattr(args, "reranker", None):
        cfg.reranker.provider = args.reranker
    pipe = RetrievalPipeline(cfg)
    stats = pipe.build(force=args.force)
    print(json.dumps(stats, indent=2))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    cfg = load_config(args.config, args.root)
    setup_logging(cfg.log_level)
    if args.provider:
        cfg.embedding.provider = args.provider
    if getattr(args, "reranker", None):
        cfg.reranker.provider = args.reranker
    pipe = RetrievalPipeline(cfg)
    pipe.load()
    result = pipe.retrieve(args.query)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 0

    if result.insufficient_evidence:
        print(result.message)
        return 0

    print(f"Query: {result.query}")
    if result.expanded_query and result.expanded_query != result.query:
        print(f"Expanded: {result.expanded_query}")
    print()
    for i, hit in enumerate(result.hits, start=1):
        c = hit.citation
        print(f"{i}. [{hit.score:.4f}] {c.file_path} — {c.heading}")
        snippet = c.paragraph.replace("\n", " ")
        if len(snippet) > 200:
            snippet = snippet[:200] + "…"
        print(f"   {snippet}")
        if c.url:
            print(f"   URL: {c.url}")
        print()
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    cfg = load_config(args.config, args.root)
    setup_logging(cfg.log_level)
    if args.provider:
        cfg.embedding.provider = args.provider
    if getattr(args, "reranker", None):
        cfg.reranker.provider = args.reranker
    pipe = RetrievalPipeline(cfg)
    # Prefer existing indexes; build with hash if missing and --build
    chunks_path = cfg.path("chunks")
    if not chunks_path.exists() or args.build:
        pipe.build(force=args.force)
    else:
        pipe.load()
    metrics = run_evaluation(
        pipe,
        generate=not args.skip_generate,
        n_questions=args.n,
    )
    print(json.dumps(metrics, indent=2))
    print(f"Report: {cfg.path('eval_report')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="retrieval",
        description="Fitness KB indexing & hybrid retrieval engine",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="Chunk, embed, and build FAISS+BM25 indexes")
    _add_common(p_build)
    p_build.add_argument("--force", action="store_true", help="Ignore incremental caches")
    p_build.add_argument(
        "--provider",
        choices=["fastembed", "openai", "hash"],
        default=None,
        help="Override embedding provider",
    )
    p_build.add_argument("--embed-model", default=None, help="Override embedding model name")
    p_build.add_argument(
        "--reranker",
        choices=["noop", "bge", "jina"],
        default=None,
        help="Override reranker provider",
    )
    p_build.set_defaults(func=cmd_build)

    p_query = sub.add_parser("query", help="Run a hybrid retrieval query")
    _add_common(p_query)
    p_query.add_argument("query", help="Natural language question")
    p_query.add_argument("--json", action="store_true", help="Emit JSON result")
    p_query.add_argument(
        "--provider",
        choices=["fastembed", "openai", "hash"],
        default=None,
        help="Override embedding provider (must match index)",
    )
    p_query.add_argument(
        "--reranker",
        choices=["noop", "bge", "jina"],
        default=None,
        help="Override reranker provider",
    )
    p_query.set_defaults(func=cmd_query)

    p_eval = sub.add_parser("eval", help="Generate questions and measure retrieval metrics")
    _add_common(p_eval)
    p_eval.add_argument("--n", type=int, default=300, help="Number of eval questions")
    p_eval.add_argument("--build", action="store_true", help="Build indexes before eval")
    p_eval.add_argument("--force", action="store_true")
    p_eval.add_argument("--skip-generate", action="store_true", help="Reuse existing questions.jsonl")
    p_eval.add_argument(
        "--provider",
        choices=["fastembed", "openai", "hash"],
        default=None,
    )
    p_eval.add_argument(
        "--reranker",
        choices=["noop", "bge", "jina"],
        default=None,
    )
    p_eval.set_defaults(func=cmd_eval)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
