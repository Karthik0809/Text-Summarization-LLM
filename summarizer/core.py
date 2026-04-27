"""Ollama-based summarization engine — llama3.1:8b, domain-aware prompting."""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Iterator

import httpx

logger = logging.getLogger(__name__)

OLLAMA_BASE  = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1:8b"

MODELS: dict[str, dict] = {
    DEFAULT_MODEL: {
        "name":  "Llama 3.1 8B",
        "badge": "Best",
        "desc":  "Meta Llama 3.1 — instruction-tuned, highly accurate summarization.",
        "size":  "4.7 GB",
    }
}

_PROMPT_DETAILED = """\
You are a professional summarization expert. Read the text below and write a clear, \
accurate, comprehensive summary.

Rules:
- Capture every key point, finding, argument, and conclusion
- Preserve all named entities, numbers, and facts exactly
- Write in clear professional prose, use paragraphs if needed
- Output ONLY the summary — no preamble, no "This text discusses…"

{domain_hint}Text:
{text}

Summary:"""

_PROMPT_BRIEF = """\
You are a professional summarization expert. Write a short, accurate summary of the text below.

Rules:
- 2-4 sentences maximum
- Keep every critical fact and number
- Output ONLY the summary — no preamble

{domain_hint}Text:
{text}

Brief Summary:"""

_DOMAIN_HINTS: dict[str, str] = {
    "scientific": "Domain focus: hypothesis, methodology, findings, conclusions.\n",
    "technical":  "Domain focus: system design, architecture, key implementation details.\n",
    "news":       "Domain focus: who, what, when, where, why, how. Lead with main event.\n",
    "finance":    "Domain focus: revenue figures, key metrics, strategic moves, outlook.\n",
    "dialogue":   "Domain focus: participants, decisions, action items, consensus reached.\n",
    "general":    "",
}


@dataclass
class SummaryResult:
    summary: str
    model_id: str
    input_tokens: int
    output_tokens: int
    compression_ratio: float
    latency_ms: float
    metadata: dict = field(default_factory=dict)


class SummarizationEngine:
    """Ollama-backed engine. One model, domain-aware prompting."""

    _instance: "SummarizationEngine | None" = None

    def __init__(self, model_id: str = DEFAULT_MODEL):
        self.model_id = model_id
        try:
            httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=5).raise_for_status()
            logger.info("Ollama OK — model: %s", self.model_id)
        except Exception as exc:
            logger.warning("Ollama unreachable (%s). Run: ollama serve && ollama pull %s", exc, self.model_id)

    @classmethod
    def get_or_create(cls, model_id: str = DEFAULT_MODEL, **_) -> "SummarizationEngine":
        if cls._instance is None:
            cls._instance = cls(model_id)
        return cls._instance

    @classmethod
    def loaded_models(cls) -> list[str]:
        try:
            r = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
            r.raise_for_status()
            return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            return []

    def _build_prompt(self, text: str, domain: str = "general", style: str = "detailed") -> str:
        hint = _DOMAIN_HINTS.get(domain, "")
        template = _PROMPT_BRIEF if style == "brief" else _PROMPT_DETAILED
        return template.format(domain_hint=hint, text=text[:6000])

    def summarize(
        self,
        text: str,
        max_length: int = 350,
        min_length: int = 50,
        domain: str = "general",
        style: str = "detailed",
        **_,
    ) -> SummaryResult:
        t0 = time.perf_counter()
        prompt = self._build_prompt(text, domain=domain, style=style)
        num_predict = 120 if style == "brief" else max(max_length * 2, 500)

        try:
            resp = httpx.post(
                f"{OLLAMA_BASE}/api/generate",
                json={
                    "model": self.model_id,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.15,
                        "num_predict": num_predict,
                        "top_p": 0.9,
                        "repeat_penalty": 1.15,
                        "stop": ["\n\n\n\n"],
                    },
                },
                timeout=180.0,
            )
            resp.raise_for_status()
            summary = resp.json().get("response", "").strip()
        except httpx.TimeoutException:
            raise RuntimeError("Ollama timed out. Is `ollama serve` running?")
        except httpx.ConnectError:
            raise RuntimeError(
                "Cannot connect to Ollama. Run: ollama serve   then: ollama pull llama3.1:8b"
            )
        except Exception as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc

        input_w  = len(text.split())
        output_w = len(summary.split())
        return SummaryResult(
            summary=summary,
            model_id=self.model_id,
            input_tokens=input_w,
            output_tokens=output_w,
            compression_ratio=round(input_w / max(output_w, 1), 2),
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
        )

    def stream(
        self,
        text: str,
        max_length: int = 350,
        domain: str = "general",
        **_,
    ) -> Iterator[str]:
        """Yield raw token chunks from Ollama streaming API."""
        prompt = self._build_prompt(text, domain=domain, style="detailed")
        try:
            with httpx.stream(
                "POST",
                f"{OLLAMA_BASE}/api/generate",
                json={
                    "model": self.model_id,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": 0.15,
                        "num_predict": max(max_length * 2, 500),
                        "top_p": 0.9,
                        "repeat_penalty": 1.15,
                    },
                },
                timeout=180.0,
            ) as resp:
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            yield token
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        except httpx.ConnectError as exc:
            raise RuntimeError("Cannot connect to Ollama. Run: ollama serve") from exc
