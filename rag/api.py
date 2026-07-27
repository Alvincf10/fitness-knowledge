"""FastAPI chat service exposing POST /chat."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from pydantic import BaseModel, Field

from .config import RagConfig, load_rag_config, setup_logging
from .context import Turn
from .pipeline import RagPipeline

logger = logging.getLogger(__name__)


class HistoryTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User fitness question")
    top_k: int | None = Field(None, ge=1, le=50, description="Optional final top-k override")
    history: list[HistoryTurn] | None = Field(
        None, description="Optional prior turns for follow-up enrichment"
    )


class SourceOut(BaseModel):
    index: int
    chunk_id: str
    title: str | None = None
    heading: str
    section: str | None = None
    file_path: str
    file: str | None = None
    category: str | None = None
    subcategory: str | None = None
    slug: str | None = None
    source: str | None = None
    url: str | None = None
    score: float = 0.0
    confidence: float = 0.0
    snippet: str = ""


class CitationOut(BaseModel):
    title: str | None = None
    file: str
    section: str | None = None
    confidence: float = 0.0


class ChatResponseOut(BaseModel):
    answer: str
    language: str = "en"
    confidence: float
    sources: list[SourceOut]
    citations: list[CitationOut] = []
    retrieval_ms: float
    rerank_ms: float
    embedding_ms: float = 0.0
    total_ms: float
    llm_ms: float = 0.0
    insufficient_knowledge: bool = False
    abstain_reason: str | None = None
    query: str = ""
    normalized_query: str = ""
    model: str | None = None


def create_app(
    config: RagConfig | None = None,
    pipeline: RagPipeline | None = None,
) -> Any:
    """Build a FastAPI application wired to a RagPipeline."""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "fastapi is required for the chat API. pip install -r requirements-rag.txt"
        ) from exc

    cfg = config or load_rag_config()
    setup_logging(cfg.log_level)
    state: dict[str, Any] = {"pipeline": pipeline, "config": cfg}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if state["pipeline"] is None:
            pipe = RagPipeline(cfg)
            pipe.load()
            state["pipeline"] = pipe
        logger.info("Chat API ready on configured host/port")
        yield

    app = FastAPI(title=cfg.api.title, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.api.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/chat", response_model=ChatResponseOut)
    def chat(body: ChatRequest) -> ChatResponseOut:
        pipe: RagPipeline | None = state.get("pipeline")
        if pipe is None:
            raise HTTPException(status_code=503, detail="Pipeline not loaded")
        if body.top_k is not None:
            pipe.config.rag.top_k_rerank = body.top_k
            pipe.config.rag.max_top_k = max(pipe.config.rag.max_top_k, body.top_k)
        history = None
        if body.history:
            history = [Turn(role=t.role, content=t.content) for t in body.history]
        try:
            result = pipe.chat(body.query, history=history, update_history=history is None)
        except Exception as exc:
            logger.exception("chat failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return ChatResponseOut(**result.to_dict())

    return app


def run_server(
    config_path: str | None = None,
    knowledge_root: str | None = None,
    *,
    host: str | None = None,
    port: int | None = None,
) -> None:
    """Start uvicorn serving POST /chat."""
    import uvicorn

    cfg = load_rag_config(config_path, knowledge_root)
    app = create_app(cfg)
    uvicorn.run(
        app,
        host=host or cfg.api.host,
        port=port or cfg.api.port,
        log_level=cfg.log_level.lower(),
    )
