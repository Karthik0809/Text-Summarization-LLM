"""
Autonomous Summarization Agent
─────────────────────────────
1. Analyzes input text (word count, domain, complexity)
2. Selects the best model for that domain
3. Generates a summary with tuned parameters
4. Self-evaluates quality against an extractive baseline (ROUGE-L)
5. Retries with a fallback model if quality is below threshold
Returns the best result with a confidence score and full reasoning trace.
"""
from __future__ import annotations

import re
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from summarizer.core import SummarizationEngine
from summarizer.evaluation import compute_rouge

logger = logging.getLogger(__name__)


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class AgentStep:
    step: int
    model_id: str
    summary: str
    rouge_l: float
    latency_ms: float
    reason: str


@dataclass
class AgentResult:
    summary: str
    model_id: str
    confidence: float          # 0.0 – 1.0
    quality_score: float       # ROUGE-L vs extractive baseline
    total_latency_ms: float
    analysis: dict
    steps: list[AgentStep]
    selected_reason: str


# ─── Domain keyword maps ───────────────────────────────────────────────────────

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "dialogue": [
        "said", "replied", "asked", "told", "conversation", "meeting",
        "discussed", "agreed", "mentioned", "explained", "responded",
    ],
    "scientific": [
        "study", "research", "findings", "hypothesis", "experiment",
        "methodology", "analysis", "results", "conclusion", "published",
        "journal", "scientists", "researchers", "evidence", "data",
    ],
    "technical": [
        "algorithm", "system", "architecture", "implementation", "api",
        "database", "framework", "docker", "kubernetes", "cloud",
        "software", "deployment", "server", "model", "training",
    ],
    "news": [
        "government", "president", "minister", "announced", "reported",
        "according", "official", "policy", "election", "said", "told",
        "monday", "tuesday", "wednesday", "thursday", "friday",
    ],
    "finance": [
        "revenue", "profit", "earnings", "quarter", "fiscal", "stock",
        "shares", "market", "investors", "billion", "million", "growth",
        "forecast", "acquisition", "merger",
    ],
}

# Best model per domain (in order: primary, fallback)
_DOMAIN_MODEL_MAP: dict[str, list[str]] = {
    "dialogue":   ["philschmid/bart-large-cnn-samsum", "sshleifer/distilbart-cnn-12-6"],
    "scientific": ["facebook/bart-large-cnn",          "sshleifer/distilbart-cnn-12-6"],
    "technical":  ["facebook/bart-large-cnn",          "sshleifer/distilbart-cnn-12-6"],
    "news":       ["sshleifer/distilbart-cnn-12-6",    "facebook/bart-large-cnn"],
    "finance":    ["sshleifer/distilbart-cnn-12-6",    "facebook/bart-large-cnn"],
    "general":    ["sshleifer/distilbart-cnn-12-6",    "facebook/bart-large-cnn"],
}

_QUALITY_THRESHOLD = 0.18   # ROUGE-L vs extractive baseline


# ─── Agent ────────────────────────────────────────────────────────────────────

class SummarizationAgent:
    """Smart orchestrator: analyze → select → summarize → evaluate → retry."""

    def analyze(self, text: str) -> dict:
        words = text.split()
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 3]
        avg_sent_len = len(words) / max(len(sentences), 1)

        # Score each domain
        text_lower = text.lower()
        scores: dict[str, int] = {}
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            scores[domain] = sum(1 for kw in keywords if kw in text_lower)

        best_domain = max(scores, key=scores.get)
        if scores[best_domain] < 2:
            best_domain = "general"

        # Dynamic generation params based on text length
        word_count = len(words)
        max_length = min(256, max(80, word_count // 4))
        min_length = max(30, max_length // 4)

        return {
            "word_count": word_count,
            "sentence_count": len(sentences),
            "avg_sentence_length": round(avg_sent_len, 1),
            "complexity": "high" if avg_sent_len > 25 else "medium" if avg_sent_len > 15 else "low",
            "domain": best_domain,
            "domain_scores": scores,
            "recommended_models": _DOMAIN_MODEL_MAP.get(best_domain, _DOMAIN_MODEL_MAP["general"]),
            "max_length": max_length,
            "min_length": min_length,
        }

    def _extractive_baseline(self, text: str) -> str:
        """Lead-N extractive summary as quality reference."""
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 5]
        n = max(1, min(3, len(sentences) // 5))
        return " ".join(sentences[:n])

    def run(self, text: str) -> AgentResult:
        t0 = time.perf_counter()
        analysis = self.analyze(text)

        extractive = self._extractive_baseline(text)
        models_queue = analysis["recommended_models"]

        steps: list[AgentStep] = []
        best: Optional[AgentStep] = None

        for i, model_id in enumerate(models_queue):
            reason = (
                f"Primary: best model for '{analysis['domain']}' domain"
                if i == 0 else
                "Fallback: quality below threshold, retrying with second model"
            )
            logger.info("Agent step %d — %s (%s)", i + 1, model_id, reason)

            try:
                engine = SummarizationEngine.get_or_create(model_id)
                result = engine.summarize(
                    text,
                    max_length=analysis["max_length"],
                    min_length=analysis["min_length"],
                )
                scores = compute_rouge([result.summary], [extractive])
                rl = scores["rougeL"]

                step = AgentStep(
                    step=i + 1,
                    model_id=model_id,
                    summary=result.summary,
                    rouge_l=round(rl, 4),
                    latency_ms=result.latency_ms,
                    reason=reason,
                )
                steps.append(step)

                if best is None or rl > best.rouge_l:
                    best = step

                if rl >= _QUALITY_THRESHOLD:
                    logger.info("Quality threshold met (ROUGE-L %.3f ≥ %.2f)", rl, _QUALITY_THRESHOLD)
                    break

            except Exception as exc:
                logger.warning("Model %s failed: %s", model_id, exc)
                continue

        if best is None:
            raise RuntimeError("All models failed during agent run.")

        total_ms = (time.perf_counter() - t0) * 1000
        confidence = min(round(best.rouge_l / _QUALITY_THRESHOLD, 3), 1.0)

        return AgentResult(
            summary=best.summary,
            model_id=best.model_id,
            confidence=confidence,
            quality_score=best.rouge_l,
            total_latency_ms=round(total_ms, 1),
            analysis=analysis,
            steps=steps,
            selected_reason=best.reason,
        )
