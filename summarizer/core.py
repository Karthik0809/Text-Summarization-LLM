"""Groq-backed summarization engine — llama-3.3-70b-versatile."""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Iterator

from groq import Groq

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.3-70b-versatile"

MODELS: dict[str, dict] = {
    DEFAULT_MODEL: {
        "name":  "Llama 3.3 70B",
        "badge": "Best",
        "desc":  "Meta Llama 3.3 70B via Groq — ultra-fast, high accuracy summarization.",
        "size":  "API",
    }
}

_SYSTEM = (
    "You are a professional summarization expert. "
    "Your summaries are accurate, comprehensive, and clearly written."
)

_DOMAIN_HINTS: dict[str, str] = {
    "scientific": "Focus on: hypothesis, methodology, key findings, and conclusions.",
    "technical":  "Focus on: architecture, design decisions, and implementation details.",
    "news":       "Lead with the main event. Cover who, what, when, where, why.",
    "finance":    "Preserve all figures, metrics, and strategic decisions exactly.",
    "dialogue":   "Capture participants, decisions made, and action items.",
    "general":    "",
}

_PROMPT_DETAILED = """\
Summarize the following text in approximately {target_words} words (about {pct}% of the original). \
Capture the key ideas, important facts, and conclusions. \
Do NOT pad or repeat — be concise and direct. \
Write in clear professional prose. Output ONLY the summary — no preamble or labels.
{hint}
Text:
{text}"""

_PROMPT_BRIEF = """\
Summarize the following text in 2-3 sentences (under 60 words). \
Keep only the single most important point and one or two supporting facts. \
Output ONLY the summary — no preamble or labels.

Text:
{text}"""


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
    _instance: "SummarizationEngine | None" = None

    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set. Add it to your .env file.")
        self.client = Groq(api_key=api_key)
        self.model_id = DEFAULT_MODEL
        logger.info("Groq engine ready — %s", self.model_id)

    @classmethod
    def get_or_create(cls, *_, **__) -> "SummarizationEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def loaded_models(cls) -> list[str]:
        return [DEFAULT_MODEL]

    def _messages(self, text: str, domain: str = "general", style: str = "detailed",
                  max_length: int = 400, min_length: int = 50) -> list[dict]:
        hint = _DOMAIN_HINTS.get(domain, "")
        input_words = len(text.split())
        if style == "brief":
            content = _PROMPT_BRIEF.format(text=text[:8000])
        else:
            # Target 25-35% of input length, clamped to [min_length, max_length]
            raw_target = max(int(input_words * 0.30), min_length)
            target_words = min(raw_target, max_length)
            pct = round(target_words / max(input_words, 1) * 100)
            hint_line = f"\nDomain hint: {hint}\n" if hint else ""
            content = _PROMPT_DETAILED.format(
                target_words=target_words, pct=pct,
                hint=hint_line, text=text[:8000]
            )
        return [
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": content},
        ]

    def summarize(
        self,
        text: str,
        max_length: int = 400,
        min_length: int = 50,
        domain: str = "general",
        style: str = "detailed",
        **_,
    ) -> SummaryResult:
        t0 = time.perf_counter()
        if style == "brief":
            max_tokens = 100
        else:
            input_words = len(text.split())
            target = min(max(int(input_words * 0.30), min_length), max_length)
            max_tokens = min(target * 2, 600)  # ~1.5 tokens/word headroom
        try:
            resp = self.client.chat.completions.create(
                model=self.model_id,
                messages=self._messages(text, domain=domain, style=style,
                                        max_length=max_length, min_length=min_length),
                temperature=0.1,
                max_tokens=max_tokens,
            )
            summary = resp.choices[0].message.content.strip()
        except Exception as exc:
            raise RuntimeError(f"Groq error: {exc}") from exc

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

    def stream(self, text: str, max_length: int = 400, domain: str = "general", **_) -> Iterator[str]:
        input_words = len(text.split())
        target = min(max(int(input_words * 0.30), 50), max_length)
        max_tokens = min(target * 2, 600)
        try:
            s = self.client.chat.completions.create(
                model=self.model_id,
                messages=self._messages(text, domain=domain, style="detailed",
                                        max_length=max_length),
                temperature=0.1,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in s:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:
            raise RuntimeError(f"Groq stream error: {exc}") from exc
