from typing import Any, Optional
from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=50, description="Text to summarize (min 50 chars)")
    model_id: str = Field("sshleifer/distilbart-cnn-12-6", description="HuggingFace model ID")
    max_length: int = Field(256, ge=50, le=512)
    min_length: int = Field(50, ge=10, le=200)
    num_beams: int = Field(4, ge=1, le=8)
    length_penalty: float = Field(2.0, ge=0.5, le=5.0)


class SummarizeResponse(BaseModel):
    summary: str
    model_id: str
    input_tokens: int
    output_tokens: int
    compression_ratio: float
    latency_ms: float


class URLRequest(BaseModel):
    url: str = Field(..., description="Web article URL")
    model_id: str = "sshleifer/distilbart-cnn-12-6"
    max_length: int = 256
    min_length: int = 50


class BatchRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=20)
    model_id: str = "sshleifer/distilbart-cnn-12-6"
    max_length: int = 256
    min_length: int = 50


class CompareRequest(BaseModel):
    text: str = Field(..., min_length=50)
    model_ids: list[str] = Field(
        default=["sshleifer/distilbart-cnn-12-6", "facebook/bart-large-cnn"]
    )
    max_length: int = 256
    min_length: int = 50


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
