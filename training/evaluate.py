"""
Standalone evaluation script: compute ROUGE on any model against CNN/DailyMail test split.

Usage:
    python training/evaluate.py --model_id sshleifer/distilbart-cnn-12-6 --n_samples 100
    python training/evaluate.py --model_id ./checkpoints --n_samples 500
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from datasets import load_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model_id", default="sshleifer/distilbart-cnn-12-6")
    p.add_argument("--n_samples", type=int, default=100)
    p.add_argument("--max_length", type=int, default=256)
    p.add_argument("--num_beams", type=int, default=4)
    p.add_argument("--output", default="evaluation_results.json")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from summarizer.core import SummarizationEngine
    from summarizer.evaluation import compute_rouge

    logger.info("Loading model %s", args.model_id)
    engine = SummarizationEngine(args.model_id)

    logger.info("Loading CNN/DailyMail test split (%d samples)", args.n_samples)
    dataset = load_dataset("cnn_dailymail", "3.0.0", split="test")
    subset = dataset.select(range(args.n_samples))

    preds, refs = [], []
    for i, sample in enumerate(subset):
        if i % 10 == 0:
            logger.info("  %d / %d", i, args.n_samples)
        result = engine.summarize(
            sample["article"],
            max_length=args.max_length,
            num_beams=args.num_beams,
        )
        preds.append(result.summary)
        refs.append(sample["highlights"])

    scores = compute_rouge(preds, refs)
    logger.info("ROUGE scores: %s", scores)

    output = {"model_id": args.model_id, "n_samples": args.n_samples, "rouge": scores}
    Path(args.output).write_text(json.dumps(output, indent=2))
    logger.info("Saved to %s", args.output)


if __name__ == "__main__":
    main()
