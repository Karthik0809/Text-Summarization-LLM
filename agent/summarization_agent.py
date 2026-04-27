"""
Autonomous Summarization Agent
────────────────────────────────
Analyze domain -> choose prompt strategy -> summarize -> ROUGE-L eval -> retry if needed.
"""
from __future__ import annotations
import re, time, logging
from dataclasses import dataclass
from typing import Optional
from summarizer.core import DEFAULT_MODEL, SummarizationEngine
from summarizer.evaluation import compute_rouge

logger = logging.getLogger(__name__)
_QUALITY_THRESHOLD = 0.15

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "dialogue":   ["said","replied","asked","told","conversation","meeting","discussed","agreed","mentioned","responded"],
    "scientific": ["study","research","findings","hypothesis","experiment","methodology","analysis","results","conclusion","published","journal","scientists","researchers","evidence","data"],
    "technical":  ["algorithm","system","architecture","implementation","api","database","framework","docker","kubernetes","cloud","software","deployment","server","model","training"],
    "news":       ["government","president","minister","announced","reported","according","official","policy","election","monday","tuesday","wednesday","thursday","friday"],
    "finance":    ["revenue","profit","earnings","quarter","fiscal","stock","shares","market","investors","billion","million","growth","forecast","acquisition","merger"],
}

_DOMAIN_STRATEGY: dict[str, dict] = {
    "dialogue":   {"style": "detailed", "max_length": 200, "min_length": 40},
    "scientific": {"style": "detailed", "max_length": 400, "min_length": 80},
    "technical":  {"style": "detailed", "max_length": 400, "min_length": 80},
    "news":       {"style": "brief",    "max_length": 150, "min_length": 30},
    "finance":    {"style": "brief",    "max_length": 200, "min_length": 40},
    "general":    {"style": "detailed", "max_length": 300, "min_length": 60},
}


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
    confidence: float
    quality_score: float
    total_latency_ms: float
    analysis: dict
    steps: list[AgentStep]
    selected_reason: str


class SummarizationAgent:
    def analyze(self, text: str) -> dict:
        words = text.split()
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 3]
        avg_sent_len = len(words) / max(len(sentences), 1)
        text_lower = text.lower()
        scores = {d: sum(1 for kw in kws if kw in text_lower) for d, kws in _DOMAIN_KEYWORDS.items()}
        best_domain = max(scores, key=scores.get)
        if scores[best_domain] < 2:
            best_domain = "general"
        strat = _DOMAIN_STRATEGY.get(best_domain, _DOMAIN_STRATEGY["general"])
        wc = len(words)
        max_length = min(strat["max_length"], max(strat["min_length"] * 2, wc // 4))
        min_length = max(strat["min_length"], max_length // 4)
        return {
            "word_count": wc,
            "sentence_count": len(sentences),
            "avg_sentence_length": round(avg_sent_len, 1),
            "complexity": "high" if avg_sent_len > 25 else "medium" if avg_sent_len > 15 else "low",
            "domain": best_domain,
            "domain_scores": scores,
            "style": strat["style"],
            "max_length": max_length,
            "min_length": min_length,
        }

    def _extractive_baseline(self, text: str) -> str:
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 5]
        n = max(1, min(3, len(sents) // 5))
        return " ".join(sents[:n])

    def run(self, text: str) -> AgentResult:
        t0 = time.perf_counter()
        analysis = self.analyze(text)
        extractive = self._extractive_baseline(text)
        engine = SummarizationEngine.get_or_create()
        strategies = [
            {"style": analysis["style"], "reason": f"Primary: {analysis['style']} style for '{analysis['domain']}' domain"},
            {"style": "detailed",        "reason": "Retry: switching to detailed style for better coverage"},
        ]
        steps: list[AgentStep] = []
        best: Optional[AgentStep] = None
        for i, strat in enumerate(strategies):
            try:
                result = engine.summarize(
                    text,
                    max_length=analysis["max_length"],
                    min_length=analysis["min_length"],
                    domain=analysis["domain"],
                    style=strat["style"],
                )
                scores = compute_rouge([result.summary], [extractive])
                rl = scores["rougeL"]
                step = AgentStep(step=i+1, model_id=DEFAULT_MODEL, summary=result.summary,
                                 rouge_l=round(rl,4), latency_ms=result.latency_ms, reason=strat["reason"])
                steps.append(step)
                if best is None or rl > best.rouge_l:
                    best = step
                if rl >= _QUALITY_THRESHOLD:
                    break
            except Exception as exc:
                logger.warning("Agent step %d failed: %s", i+1, exc)
                continue
        if best is None:
            raise RuntimeError("All agent steps failed. Is Ollama running?")
        total_ms = (time.perf_counter() - t0) * 1000
        return AgentResult(
            summary=best.summary, model_id=DEFAULT_MODEL,
            confidence=min(round(best.rouge_l / _QUALITY_THRESHOLD, 3), 1.0),
            quality_score=best.rouge_l, total_latency_ms=round(total_ms, 1),
            analysis=analysis, steps=steps, selected_reason=best.reason,
        )
