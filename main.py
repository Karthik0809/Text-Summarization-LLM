"""
FastAPI application — serves the HTML/CSS/JS frontend AND the REST API.
Entry point for HuggingFace Spaces (port 7860).

Run locally:
    uvicorn main:app --reload --port 7860
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # loads GROQ_API_KEY from .env

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Text Summarization API v3 starting — serving on :7860")
    yield
    logger.info("Shutdown complete")


app = FastAPI(
    title="Advanced Text Summarization API",
    description=(
        "Production-grade multi-model summarization with AI agent orchestration. "
        "Supports BART · PEGASUS · T5 · text / PDF / URL inputs · streaming."
    ),
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API
app.include_router(router, prefix="/api/v1")

# Static assets (JS, CSS, images)
app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR / "static"),
    name="static",
)


# Catch-all: serve the SPA for every non-API route
@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str = ""):
    # Don't intercept API or static routes
    if full_path.startswith(("api/", "static/")):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    return FileResponse(FRONTEND_DIR / "index.html")
