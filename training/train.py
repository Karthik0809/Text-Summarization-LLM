"""
Fine-tune BART/DistilBART on CNN/DailyMail with modern HuggingFace practices.

Usage:
    python training/train.py --model_id sshleifer/distilbart-cnn-12-6 \
        --train_samples 10000 --eval_samples 1000 --epochs 3 --fp16

Push to HuggingFace Hub:
    python training/train.py ... --push_to_hub --hub_model_id YOUR_HF_USERNAME/model-name
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import evaluate
import numpy as np
from datasets import load_dataset
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    EarlyStoppingCallback,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fine-tune a seq2seq model for summarization")
    p.add_argument("--model_id", default="sshleifer/distilbart-cnn-12-6")
    p.add_argument("--output_dir", default="./checkpoints")
    p.add_argument("--train_samples", type=int, default=10_000)
    p.add_argument("--eval_samples", type=int, default=1_000)
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch_size", type=int, default=4)
    p.add_argument("--grad_accum", type=int, default=4, help="Gradient accumulation steps")
    p.add_argument("--learning_rate", type=float, default=2e-5)
    p.add_argument("--max_input", type=int, default=1024)
    p.add_argument("--max_target", type=int, default=256)
    p.add_argument("--fp16", action="store_true", help="Enable mixed-precision training (GPU only)")
    p.add_argument("--push_to_hub", action="store_true")
    p.add_argument("--hub_model_id", default=None)
    return p.parse_args()


def preprocess(examples, tokenizer, max_input: int, max_target: int) -> dict:
    model_inputs = tokenizer(
        examples["article"], max_length=max_input, truncation=True, padding=False
    )
    labels = tokenizer(
        examples["highlights"], max_length=max_target, truncation=True, padding=False
    )
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs


def build_compute_metrics(tokenizer, rouge_metric):
    def compute_metrics(eval_preds):
        preds, labels = eval_preds
        labels = np.where(labels != -100, labels, tokenizer.pad_token_id)
        decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)
        decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)

        # Sentence-split for rougeLsum
        decoded_preds = ["\n".join(p.strip().split(". ")) for p in decoded_preds]
        decoded_labels = ["\n".join(l.strip().split(". ")) for l in decoded_labels]

        result = rouge_metric.compute(
            predictions=decoded_preds, references=decoded_labels, use_stemmer=True
        )
        result = {k: round(v * 100, 4) for k, v in result.items()}
        result["gen_len"] = float(np.mean([np.count_nonzero(p != tokenizer.pad_token_id) for p in preds]))
        return result

    return compute_metrics


def main() -> None:
    args = parse_args()
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("Model  : %s", args.model_id)
    logger.info("Output : %s", output_path)

    logger.info("Loading CNN/DailyMail dataset…")
    dataset = load_dataset("cnn_dailymail", "3.0.0")

    train_ds = dataset["train"].select(range(args.train_samples))
    eval_ds = dataset["validation"].select(range(args.eval_samples))

    logger.info("Loading tokenizer and model…")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model_id)

    logger.info("Tokenising…")
    fn = lambda ex: preprocess(ex, tokenizer, args.max_input, args.max_target)
    train_ds = train_ds.map(fn, batched=True, remove_columns=train_ds.column_names)
    eval_ds = eval_ds.map(fn, batched=True, remove_columns=eval_ds.column_names)

    rouge_metric = evaluate.load("rouge")
    data_collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model, padding=True)

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(output_path),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        warmup_steps=500,
        weight_decay=0.01,
        learning_rate=args.learning_rate,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="rougeL",
        greater_is_better=True,
        fp16=args.fp16,
        predict_with_generate=True,
        generation_max_length=args.max_target,
        logging_dir=str(output_path / "logs"),
        logging_steps=100,
        report_to="none",
        push_to_hub=args.push_to_hub,
        hub_model_id=args.hub_model_id,
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=build_compute_metrics(tokenizer, rouge_metric),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    logger.info("Training…")
    trainer.train()
    trainer.save_model(str(output_path))
    tokenizer.save_pretrained(str(output_path))

    final_metrics = trainer.evaluate(eval_ds)
    logger.info("Final metrics: %s", final_metrics)
    (output_path / "training_metrics.json").write_text(json.dumps(final_metrics, indent=2))

    logger.info("Done. Model saved to %s", output_path)
    if args.push_to_hub:
        logger.info("Pushed to HuggingFace Hub: %s", args.hub_model_id)


if __name__ == "__main__":
    main()
