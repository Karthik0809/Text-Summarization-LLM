"""Evaluation metrics: ROUGE and optional BERTScore."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    rouge1: float
    rouge2: float
    rougeL: float
    rougeLsum: float
    bert_score_f1: Optional[float]
    compression_ratio: float
    avg_sentence_length: float


def compute_rouge(predictions: list[str], references: list[str]) -> dict[str, float]:
    from rouge_score import rouge_scorer

    scorer = rouge_scorer.RougeScorer(
        ["rouge1", "rouge2", "rougeL", "rougeLsum"], use_stemmer=True
    )
    buckets: dict[str, list[float]] = {k: [] for k in ["rouge1", "rouge2", "rougeL", "rougeLsum"]}
    for pred, ref in zip(predictions, references):
        scores = scorer.score(ref, pred)
        for key in buckets:
            buckets[key].append(scores[key].fmeasure)
    return {k: round(sum(v) / len(v), 4) for k, v in buckets.items()}


def compute_bert_score(predictions: list[str], references: list[str]) -> Optional[float]:
    try:
        from bert_score import score as bs

        _, _, F1 = bs(predictions, references, lang="en", verbose=False)
        return round(float(F1.mean().item()), 4)
    except ImportError:
        logger.warning("bert-score not installed; skipping BERTScore.")
        return None


def evaluate_single(summary: str, reference: str) -> EvaluationResult:
    rouge = compute_rouge([summary], [reference])
    words = summary.split()
    sentences = [s for s in re.split(r"[.!?]", summary) if s.strip()]

    return EvaluationResult(
        rouge1=rouge["rouge1"],
        rouge2=rouge["rouge2"],
        rougeL=rouge["rougeL"],
        rougeLsum=rouge["rougeLsum"],
        bert_score_f1=None,
        compression_ratio=round(len(reference.split()) / max(len(words), 1), 2),
        avg_sentence_length=round(len(words) / max(len(sentences), 1), 1),
    )
