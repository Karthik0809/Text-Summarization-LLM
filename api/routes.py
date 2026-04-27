"""All API endpoints."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from typing import Any

import torch
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
from summarizer.core import MODELS, SummarizationEngine
from summarizer.ingestion import extract_from_pdf, extract_from_url

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _engine(model_id: str) -> SummarizationEngine:
    try:
        return SummarizationEngine.get_or_create(model_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Model load failed: {exc}") from exc


# ─── Meta ─────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="3.0.0",
        cuda_available=torch.cuda.is_available(),
        loaded_models=SummarizationEngine.loaded_models(),
    )


@router.get("/models", response_model=list[ModelInfo], tags=["meta"])
async def list_models() -> list[ModelInfo]:
    return [ModelInfo(model_id=mid, **info) for mid, info in MODELS.items()]


# ─── Summarize ────────────────────────────────────────────────────────────────

@router.post("/summarize", response_model=SummarizeResponse, tags=["summarize"])
async def summarize_text(req: SummarizeRequest) -> SummarizeResponse:
    result = _engine(req.model_id).summarize(
        req.text,
        max_length=req.max_length,
        min_length=req.min_length,
        num_beams=req.num_beams,
        length_penalty=req.length_penalty,
    )
    return SummarizeResponse(**result.__dict__)


@router.post("/summarize/stream", tags=["summarize"])
async def summarize_stream(req: SummarizeRequest):
    """Server-Sent Events streaming endpoint — yields tokens as they are generated."""
    engine = _engine(req.model_id)

    async def event_stream():
        gen = engine.stream(
            req.text,
            max_length=req.max_length,
            min_length=req.min_length,
        )
        loop = asyncio.get_event_loop()

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
    result = _engine(req.model_id).summarize(text, max_length=req.max_length, min_length=req.min_length)
    return {**result.__dict__, "title": title, "source_url": req.url}


@router.post("/summarize/pdf", tags=["summarize"])
async def summarize_pdf(
    file: UploadFile = File(...),
    model_id: str = Query("sshleifer/distilbart-cnn-12-6"),
    max_length: int = Query(256),
    min_length: int = Query(50),
) -> dict[str, Any]:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are supported.")
    try:
        content = await file.read()
        text = extract_from_pdf(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"PDF extraction failed: {exc}") from exc
    result = _engine(model_id).summarize(text[:4000], max_length=max_length, min_length=min_length)
    return {**result.__dict__, "filename": file.filename, "extracted_words": len(text.split())}


@router.post("/summarize/batch", tags=["summarize"])
async def summarize_batch(req: BatchRequest) -> dict[str, Any]:
    engine = _engine(req.model_id)
    results = []
    for text in req.texts:
        try:
            r = engine.summarize(text, max_length=req.max_length, min_length=req.min_length)
            results.append({**r.__dict__, "status": "ok"})
        except Exception as exc:
            results.append({"status": "error", "detail": str(exc)})
    return {"results": results, "count": len(results), "model_id": req.model_id}


@router.post("/compare", tags=["summarize"])
async def compare_models(req: CompareRequest) -> dict[str, Any]:
    comparison: dict[str, Any] = {}
    for model_id in req.model_ids:
        try:
            result = _engine(model_id).summarize(
                req.text, max_length=req.max_length, min_length=req.min_length
            )
            comparison[model_id] = {**result.__dict__, "status": "ok"}
        except Exception as exc:
            comparison[model_id] = {"status": "error", "detail": str(exc)}
    return {"text_preview": req.text[:200] + "...", "results": comparison}


# ─── AI Agent ─────────────────────────────────────────────────────────────────

@router.post("/agent/run", response_model=AgentResponse, tags=["agent"])
async def run_agent(req: AgentRequest) -> AgentResponse:
    """
    AI Agent endpoint: automatically analyzes the text, selects the best model,
    evaluates quality, and retries if below threshold.
    """
    from agent.summarization_agent import SummarizationAgent
    try:
        agent = SummarizationAgent()
        result = await asyncio.get_event_loop().run_in_executor(None, agent.run, req.text)
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
