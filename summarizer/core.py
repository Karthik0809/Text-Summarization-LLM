"""Multi-model summarization engine with caching and streaming support."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from threading import Thread
from typing import Iterator

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, TextIteratorStreamer

logger = logging.getLogger(__name__)

MODELS: dict[str, dict] = {
    "sshleifer/distilbart-cnn-12-6": {
        "name": "DistilBART (Recommended)",
        "badge": "⚡ Fast",
        "desc": "2× faster than BART, 97% quality. Best for demos & CPU.",
        "size": "306 MB",
    },
    "facebook/bart-large-cnn": {
        "name": "BART Large CNN",
        "badge": "🏆 Best Quality",
        "desc": "Highest quality. Fine-tuned on CNN/DailyMail.",
        "size": "1.6 GB",
    },
    "google/pegasus-cnn_dailymail": {
        "name": "PEGASUS CNN/DM",
        "badge": "⚖️ Balanced",
        "desc": "Google's abstractive model. Strong on news.",
        "size": "2.3 GB",
    },
    "t5-base": {
        "name": "T5 Base",
        "badge": "🪶 Lightweight",
        "desc": "Google T5 text-to-text. Compact and versatile.",
        "size": "892 MB",
    },
    "philschmid/bart-large-cnn-samsum": {
        "name": "BART Dialogue",
        "badge": "💬 Dialogue",
        "desc": "BART fine-tuned on SAMSum. Excellent for meeting notes.",
        "size": "1.6 GB",
    },
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
    """Thread-safe multi-model engine with per-model caching."""

    _cache: dict[str, "SummarizationEngine"] = {}

    def __init__(self, model_id: str, device: str = "auto"):
        self.model_id = model_id
        self.device = self._resolve_device(device)
        self._load()

    @classmethod
    def get_or_create(cls, model_id: str, device: str = "auto") -> "SummarizationEngine":
        if model_id not in cls._cache:
            logger.info("Loading model %s", model_id)
            cls._cache[model_id] = cls(model_id, device)
        return cls._cache[model_id]

    @classmethod
    def loaded_models(cls) -> list[str]:
        return list(cls._cache.keys())

    def _resolve_device(self, device: str) -> str:
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device

    def _load(self) -> None:
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            self.model_id, torch_dtype=dtype
        ).to(self.device)
        self.model.eval()
        logger.info("Loaded %s on %s", self.model_id, self.device)

    def _prepare_text(self, text: str) -> str:
        if "t5" in self.model_id.lower():
            return f"summarize: {text}"
        return text

    def summarize(
        self,
        text: str,
        max_length: int = 256,
        min_length: int = 50,
        num_beams: int = 4,
        length_penalty: float = 2.0,
        no_repeat_ngram_size: int = 3,
    ) -> SummaryResult:
        t0 = time.perf_counter()
        text = self._prepare_text(text)

        inputs = self.tokenizer(
            text, return_tensors="pt", max_length=1024, truncation=True
        ).to(self.device)

        input_tokens = int(inputs["input_ids"].shape[1])

        with torch.no_grad():
            output_ids = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_length=max_length,
                min_length=min_length,
                num_beams=num_beams,
                length_penalty=length_penalty,
                no_repeat_ngram_size=no_repeat_ngram_size,
                early_stopping=True,
            )

        summary = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        output_tokens = int(output_ids.shape[1])
        latency_ms = (time.perf_counter() - t0) * 1000

        return SummaryResult(
            summary=summary,
            model_id=self.model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            compression_ratio=round(input_tokens / max(output_tokens, 1), 2),
            latency_ms=round(latency_ms, 1),
        )

    def stream(
        self,
        text: str,
        max_length: int = 256,
        min_length: int = 30,
    ) -> Iterator[str]:
        """Yield decoded tokens one at a time for streaming UI."""
        text = self._prepare_text(text)
        inputs = self.tokenizer(
            text, return_tensors="pt", max_length=1024, truncation=True
        ).to(self.device)

        streamer = TextIteratorStreamer(
            self.tokenizer, skip_special_tokens=True, skip_prompt=True
        )
        gen_kwargs = {
            **inputs,
            "max_length": max_length,
            "min_length": min_length,
            "do_sample": True,
            "temperature": 0.7,
            "streamer": streamer,
        }
        thread = Thread(target=self.model.generate, kwargs=gen_kwargs, daemon=True)
        thread.start()
        yield from streamer
        thread.join()
