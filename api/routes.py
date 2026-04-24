import logging
from typing import Any

import torch
from fastapi import APIRouter, HTTPException, UploadFile, File, Query

from api.schemas import (
    BatchRequest,
    CompareRequest,
    HealthResponse,
    ModelInfo,
    SummarizeRequest,
    SummarizeResponse,
    URLRequest,
)
from summarizer.core import MODELS, SummarizationEngine
from summarizer.ingestion import extract_from_pdf, extract_from_url

logger = logging.getLogger(__name__)
router = APIRouter()


def _engine(model_id: str) -> SummarizationEngine:
    try:
        return SummarizationEngine.get_or_create(model_id)
    except Exception as exc:
        logger.exception("Failed to load model %s", model_id)
        raise HTTPException(status_code=500, detail=f"Model load failed: {exc}") from exc


# ─── Health ───────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="2.0.0",
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


@router.post("/summarize/url", tags=["summarize"])
async def summarize_url(req: URLRequest) -> dict[str, Any]:
    try:
        title, text = extract_from_url(req.url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if len(text.split()) < 30:
        raise HTTPException(status_code=422, detail="Extracted text too short to summarize.")

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
