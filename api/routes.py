"""All API endpoints."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse

from api.schemas import (
    AgentRequest, AgentResponse,
    BatchRequest,
    CompareRequest,
    HealthResponse,
    ModelInfo,
    SummarizeRequest, SummarizeResponse,
    URLRequest,
)
from summarizer.core import DEFAULT_MODEL, MODELS, SummarizationEngine
from summarizer.ingestion import extract_from_pdf, extract_from_url

logger = logging.getLogger(__name__)
router = APIRouter()


def _engine() -> SummarizationEngine:
    try:
        return SummarizationEngine.get_or_create()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ─── Meta ─────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="4.0.0",
        cuda_available=False,
        loaded_models=SummarizationEngine.loaded_models(),
    )


@router.get("/models", response_model=list[ModelInfo], tags=["meta"])
async def list_models() -> list[ModelInfo]:
    return [ModelInfo(model_id=mid, **info) for mid, info in MODELS.items()]


# ─── Summarize ────────────────────────────────────────────────────────────────

@router.post("/summarize", response_model=SummarizeResponse, tags=["summarize"])
async def summarize_text(req: SummarizeRequest) -> SummarizeResponse:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _engine().summarize(req.text, max_length=req.max_length, min_length=req.min_length),
    )
    return SummarizeResponse(**result.__dict__)


@router.post("/summarize/stream", tags=["summarize"])
async def summarize_stream(req: SummarizeRequest):
    """SSE streaming endpoint — yields tokens as Ollama generates them."""
    engine = _engine()

    async def event_stream():
        loop = asyncio.get_event_loop()
        gen = engine.stream(req.text, max_length=req.max_length)

        def _next():
            try:
                return next(gen)
            except StopIteration:
                return None

        try:
            while True:
                token = await loop.run_in_executor(None, _next)
                if token is None:
                    yield "data: [DONE]\n\n"
                    break
                safe = token.replace("\n", " ").replace("\r", "")
                if safe.strip():
                    yield f"data: {safe}\n\n"
        except Exception as exc:
            yield f"data: [ERROR] {exc}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/summarize/url", tags=["summarize"])
async def summarize_url(req: URLRequest) -> dict[str, Any]:
    try:
        title, text = extract_from_url(req.url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if len(text.split()) < 30:
        raise HTTPException(status_code=422, detail="Extracted text too short.")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _engine().summarize(text, max_length=req.max_length, min_length=req.min_length),
    )
    return {**result.__dict__, "title": title, "source_url": req.url, "extracted_words": len(text.split())}


@router.post("/summarize/pdf", tags=["summarize"])
async def summarize_pdf(
    file: UploadFile = File(...),
    max_length: int = Query(350),
    min_length: int = Query(50),
) -> dict[str, Any]:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are supported.")
    try:
        content = await file.read()
        text = extract_from_pdf(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"PDF extraction failed: {exc}") from exc
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _engine().summarize(text[:6000], max_length=max_length, min_length=min_length),
    )
    return {**result.__dict__, "filename": file.filename, "extracted_words": len(text.split())}


@router.post("/summarize/batch", tags=["summarize"])
async def summarize_batch(req: BatchRequest) -> dict[str, Any]:
    loop = asyncio.get_event_loop()
    results = []

    async def _one(text: str):
        try:
            r = await loop.run_in_executor(
                None,
                lambda: _engine().summarize(text, max_length=req.max_length, min_length=req.min_length),
            )
            return {**r.__dict__, "status": "ok"}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    results = await asyncio.gather(*[_one(t) for t in req.texts])
    return {"results": list(results), "count": len(results), "model_id": DEFAULT_MODEL}


@router.post("/compare", tags=["summarize"])
async def compare_styles(req: CompareRequest) -> dict[str, Any]:
    """Compare Brief vs Detailed summarization style on the same model."""
    loop = asyncio.get_event_loop()

    async def _run(style: str, max_len: int, min_len: int):
        try:
            r = await loop.run_in_executor(
                None,
                lambda: _engine().summarize(req.text, max_length=max_len, min_length=min_len, style=style),
            )
            return style, {**r.__dict__, "status": "ok"}
        except Exception as exc:
            return style, {"status": "error", "detail": str(exc)}

    pairs = await asyncio.gather(
        _run("brief",    100, 20),
        _run("detailed", 400, 80),
    )
    results = {k: v for k, v in pairs}
    return {"text_preview": req.text[:200] + "...", "results": results}


# ─── AI Agent ─────────────────────────────────────────────────────────────────

@router.post("/agent/run", response_model=AgentResponse, tags=["agent"])
async def run_agent(req: AgentRequest) -> AgentResponse:
    from agent.summarization_agent import SummarizationAgent
    try:
        agent = SummarizationAgent()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, agent.run, req.text)
        return AgentResponse(
            summary=result.summary,
            model_id=result.model_id,
            confidence=result.confidence,
            quality_score=result.quality_score,
            total_latency_ms=result.total_latency_ms,
            analysis=result.analysis,
            steps=[asdict(s) for s in result.steps],
            selected_reason=result.selected_reason,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
