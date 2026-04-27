from typing import Any, Optional
from pydantic import BaseModel, Field

_MODEL = "llama3.1:8b"


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=20)
    model_id: str = Field(_MODEL)
    max_length: int = Field(350, ge=50, le=600)
    min_length: int = Field(50, ge=10, le=200)
    num_beams: int = Field(1, ge=1, le=8)
    length_penalty: float = Field(1.0, ge=0.5, le=5.0)


class SummarizeResponse(BaseModel):
    summary: str
    model_id: str
    input_tokens: int
    output_tokens: int
    compression_ratio: float
    latency_ms: float


class URLRequest(BaseModel):
    url: str
    model_id: str = _MODEL
    max_length: int = 350
    min_length: int = 50


class BatchRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=20)
    model_id: str = _MODEL
    max_length: int = 350
    min_length: int = 50


class CompareRequest(BaseModel):
    text: str = Field(..., min_length=20)
    model_ids: list[str] = Field(default=[_MODEL])
    max_length: int = 350
    min_length: int = 50


class AgentRequest(BaseModel):
    text: str = Field(..., min_length=20, description="Text for the AI agent to summarize")


class AgentResponse(BaseModel):
    summary: str
    model_id: str
    confidence: float
    quality_score: float
    total_latency_ms: float
    analysis: dict[str, Any]
    steps: list[dict[str, Any]]
    selected_reason: str


class ModelInfo(BaseModel):
    model_id: str
    name: str
    badge: str
    desc: str
    size: str


class HealthResponse(BaseModel):
    status: str
    version: str
    cuda_available: bool
    loaded_models: list[str]
