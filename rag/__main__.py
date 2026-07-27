"""CLI: chat / serve / eval / calibrate / benchmark for the RAG pipeline."""

from __future__ import annotations

import argparse
import json
import logging

from .api import run_server
from .benchmark_phase45 import run_phase45_benchmark
from .calibrate import run_confidence_calibration
from .citations import format_sources_markdown
from .config import load_rag_config, setup_logging
from .evaluate import run_rag_evaluation
from .pipeline import RagPipeline
from retrieval.reranker import NoOpReranker

logger = logging.getLogger(__name__)


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default=None, help="Path to config/rag.yaml")
    parser.add_argument("--root", default=None, help="Knowledge root directory")


def _apply_overrides(cfg, args) -> None:
    if getattr(args, "llm", None):
        cfg.llm.provider = args.llm
    if getattr(args, "reranker", None):
        cfg.reranker.provider = args.reranker
        cfg.retrieval.reranker.provider = args.reranker
        cfg.rag.enable_reranker = args.reranker != "noop"
    if getattr(args, "no_rerank", False):
        cfg.rag.enable_reranker = False
        cfg.reranker.provider = "noop"
        cfg.retrieval.reranker.provider = "noop"


def _make_pipeline(cfg, args) -> RagPipeline:
    _apply_overrides(cfg, args)
    backend = NoOpReranker() if not cfg.rag.enable_reranker else None
    return RagPipeline(cfg, reranker_backend=backend)


def cmd_chat(args: argparse.Namespace) -> int:
    cfg = load_rag_config(args.config, args.root)
    setup_logging(cfg.log_level)
    pipe = _make_pipeline(cfg, args)
    pipe.load()
    result = pipe.chat(args.query)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 0
    print(result.answer)
    print()
    if result.citations:
        print("Citations:")
        for c in result.citations:
            print(f"  - {c.get('title')} | {c.get('file')} | {c.get('section')} | conf={c.get('confidence')}")
    elif result.sources:
        print("Sources:")
        print(format_sources_markdown(result.sources))
    print(
        f"\nlanguage={result.language} confidence={result.confidence:.3f} "
        f"retrieval_ms={result.retrieval_ms:.1f} rerank_ms={result.rerank_ms:.1f} "
        f"total_ms={result.total_ms:.1f}"
    )
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    run_server(args.config, args.root, host=args.host, port=args.port)
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    cfg = load_rag_config(args.config, args.root)
    setup_logging(cfg.log_level)
    pipe = _make_pipeline(cfg, args)
    pipe.load()
    metrics = run_rag_evaluation(
        pipe,
        cfg,
        n_retrieval=args.n_retrieval,
        n_hallucination=args.n_hallucination,
        regenerate_hallucination=not args.skip_generate_hallucination,
    )
    print(json.dumps(metrics.to_dict(), indent=2))
    print(f"Report: {cfg.resolve(cfg.eval.report_path)}")
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    cfg = load_rag_config(args.config, args.root)
    setup_logging(cfg.log_level)
    pipe = _make_pipeline(cfg, args)
    pipe.load()
    rows, recommended = run_confidence_calibration(
        pipe,
        cfg,
        n_retrieval=args.n_retrieval,
        n_hallucination=args.n_hallucination,
    )
    print(json.dumps({"recommended": recommended.to_dict(), "rows": [r.to_dict() for r in rows]}, indent=2))
    print(f"Report: {cfg.resolve(cfg.eval.confidence_report_path)}")
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    cfg = load_rag_config(args.config, args.root)
    setup_logging(cfg.log_level)
    pipe = _make_pipeline(cfg, args)
    pipe.load()
    metrics = run_phase45_benchmark(
        pipe,
        cfg,
        n_retrieval=args.n_retrieval,
        n_hallucination=args.n_hallucination,
    )
    print(json.dumps(metrics.to_dict(), indent=2))
    print(f"Report: {cfg.resolve(cfg.eval.benchmark_report_path)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rag",
        description="Fitness KB RAG pipeline (Phase 4.5)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_model_flags(p: argparse.ArgumentParser) -> None:
        p.add_argument("--llm", choices=["extractive", "openai", "mock"], default=None)
        p.add_argument("--reranker", choices=["noop", "bge", "jina"], default=None)
        p.add_argument("--no-rerank", action="store_true", help="Force noop reranker (fast CPU)")

    p_chat = sub.add_parser("chat", help="Answer a question via RAG")
    _add_common(p_chat)
    p_chat.add_argument("query", help="Natural language question")
    p_chat.add_argument("--json", action="store_true")
    add_model_flags(p_chat)
    p_chat.set_defaults(func=cmd_chat)

    p_serve = sub.add_parser("serve", help="Start FastAPI POST /chat server")
    _add_common(p_serve)
    p_serve.add_argument("--host", default=None)
    p_serve.add_argument("--port", type=int, default=None)
    p_serve.set_defaults(func=cmd_serve)

    p_eval = sub.add_parser("eval", help="Retrieval + hallucination benchmarks")
    _add_common(p_eval)
    p_eval.add_argument("--n-retrieval", type=int, default=None)
    p_eval.add_argument("--n-hallucination", type=int, default=100)
    p_eval.add_argument("--skip-generate-hallucination", action="store_true")
    add_model_flags(p_eval)
    p_eval.set_defaults(func=cmd_eval)

    p_cal = sub.add_parser("calibrate", help="Sweep confidence thresholds → confidence_report.md")
    _add_common(p_cal)
    p_cal.add_argument("--n-retrieval", type=int, default=100)
    p_cal.add_argument("--n-hallucination", type=int, default=100)
    add_model_flags(p_cal)
    p_cal.set_defaults(func=cmd_calibrate)

    p_bench = sub.add_parser("benchmark", help="Phase 4.5 production benchmark suite")
    _add_common(p_bench)
    p_bench.add_argument("--n-retrieval", type=int, default=100)
    p_bench.add_argument("--n-hallucination", type=int, default=100)
    add_model_flags(p_bench)
    p_bench.set_defaults(func=cmd_benchmark)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
