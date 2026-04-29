---
title: Advanced Text Summarization with BART
emoji: 🔬
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: true
license: mit
---

# Text Summarization — AI Agent + Groq

[![CI](https://github.com/Karthik0809/Text-Summarization-LLM/actions/workflows/ci.yml/badge.svg)](https://github.com/Karthik0809/Text-Summarization-LLM/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Live Demo](https://img.shields.io/badge/🤗%20HF%20Spaces-Live%20Demo-orange)](https://huggingface.co/spaces/karthikmulugu08/text-summarizer)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](Dockerfile)

> **Live Demo →** [huggingface.co/spaces/karthikmulugu08/text-summarizer](https://huggingface.co/spaces/karthikmulugu08/text-summarizer)

End-to-end abstractive text summarization project — started with fine-tuning **facebook/bart-large-cnn** on CNN/DailyMail (ROUGE-L 0.41), iterated through multi-model transformer support (BART · PEGASUS · T5 · DistilBART), local inference via **Ollama (Llama 3.1 8B)**, and production deployment via **Groq (Llama 3.3 70B)**. Ships with a custom dark-mode HTML/CSS/JS SPA, FastAPI REST backend, autonomous AI agent, real-time streaming, and multi-modal input.

---

## What Was Built

| Area | Details |
|---|---|
| **Fine-tuning** | facebook/bart-large-cnn on CNN/DailyMail (300K+ pairs) — ROUGE-L 0.41, competitive with published baselines |
| **Multi-model** | BART Large, DistilBART, PEGASUS, T5 — switchable per request |
| **Local inference** | Ollama + Llama 3.1 8B — zero cloud dependency |
| **Production LLM** | Groq API — Llama 3.3 70B; responses under 2 s |
| **Prompt engineering** | Domain-aware prompts (6 domains) with exhaustive fact-preservation rules; Detailed / Brief styles |
| **AI Agent** | Keyword-based domain detection → strategy selection → summarize → ROUGE-L quality score → auto-retry |
| **Streaming** | Real-time token-by-token output via Groq streaming API |
| **Multi-modal input** | Plain text · PDF (pdfplumber) · Web URL (trafilatura) |
| **Batch processing** | Manual `---` separator or CSV upload; full-text CSV download |
| **ROUGE Evaluation** | ROUGE-1/2/L computed client-side in vanilla JS; radar chart + gauge bars drawn on Canvas |
| **UI** | Custom dark-mode HTML/CSS/JS SPA — no framework; 5 feature tabs |
| **Export** | TXT · JSON · Markdown |
| **History** | Session history persisted in `localStorage` |
| **REST API** | FastAPI + Pydantic v2 + Swagger UI + CORS |
| **Docker** | Single Dockerfile, runs on port 7860 |
| **CI/CD** | GitHub Actions → pytest + ruff → auto-deploy to HuggingFace Spaces |

---

## Five Feature Tabs

### Summarize
Pick a **domain** (General · News · Scientific · Technical · Finance · Dialogue) and **style** (Detailed or Brief). Input via text area, PDF drop-zone, or URL fetch. Real-time streaming toggle. Metrics (input/output words, compression ratio, latency) displayed inline. Export as TXT, JSON, or Markdown.

### Compare
Run the same text through **Brief** and **Detailed** prompt strategies side-by-side. Canvas bar chart shows output length for each style.

### Batch
Summarize up to 20 texts at once — separate with `---` or upload a CSV with a `text` column. Expandable per-row previews. Download all results as CSV.

### Evaluate
ROUGE-1, ROUGE-2, and ROUGE-L computed **entirely in the browser** (no server round-trip) via a custom vanilla JS implementation. Results displayed as gauge bars and a Canvas radar chart.

### AI Agent
Fully autonomous 4-step pipeline:
1. **Analyze** — counts words, detects domain via keyword scoring, measures complexity
2. **Select strategy** — picks prompt style and token budget for the detected domain
3. **Summarize** — calls Llama 3.3 70B via Groq
4. **Evaluate** — scores with ROUGE-L against an extractive baseline; retries with alternate strategy if below threshold

Animated step tracker, confidence ring (SVG), and text-analysis breakdown panel.

---

## Model & Inference Evolution

```
Phase 1 — Fine-tuning
  facebook/bart-large-cnn  ──►  CNN/DailyMail (300K pairs, 3 epochs)
  Seq2SeqTrainer + early stopping + ROUGE-L metric  ──►  ROUGE-L 0.41

Phase 2 — Multi-model transformer API
  BART Large · DistilBART · PEGASUS · T5
  Switchable per request via model registry

Phase 3 — Local LLM (Ollama)
  Llama 3.1 8B  ──►  zero cloud cost, tested locally

Phase 4 — Production (Groq)
  Llama 3.3 70B Versatile  ──►  sub-2s latency, deployed on HF Spaces
```

---

## Prompt Engineering

All prompts follow exhaustive fact-preservation rules:
- Keep every named entity, date, number, statistic, and percentage exactly as written
- Preserve causal relationships (why something happened)
- Keep quoted statements with speaker and tense
- Never collapse two separate points into one
- Remove only filler phrases and direct repetition

Six domain hints layer on top: scientific focuses on hypothesis/findings/conclusions; news leads with main event + who/what/when/where/why; finance preserves all figures and strategic decisions exactly; etc.

---

## Architecture

```
Input (Text / PDF / URL)
        │
        ▼
FastAPI  /api/v1            ◄──  HTML/CSS/JS SPA  (frontend/)
├── POST /summarize
├── POST /summarize/url
├── POST /summarize/pdf
├── POST /summarize/batch
├── POST /compare
└── POST /agent/run
        │
        ▼
Groq API — Llama 3.3 70B
(domain-aware prompt · detailed / brief · streaming)
        │
        ▼
SummaryResult {summary, input_tokens, output_tokens,
               compression_ratio, latency_ms}
```

---

## Quick Start

```bash
git clone https://github.com/Karthik0809/Text-Summarization-LLM.git
cd Text-Summarization-LLM

pip install -r requirements.txt

cp .env.example .env
# set GROQ_API_KEY=your_key  (free at console.groq.com)

uvicorn main:app --reload --port 7860
# App  → http://localhost:7860
# Docs → http://localhost:7860/api/docs
```

### Docker

```bash
docker build -t text-summarizer .
docker run -p 7860:7860 -e GROQ_API_KEY=your_key text-summarizer
```

### Fine-tune (optional)

```bash
python training/train.py \
  --model_id facebook/bart-large-cnn \
  --train_samples 10000 \
  --epochs 3 --batch_size 4 --fp16
```

---

## REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/v1/health`          | Status + loaded model |
| `GET`  | `/api/v1/models`          | Available models |
| `POST` | `/api/v1/summarize`       | Summarize plain text |
| `POST` | `/api/v1/summarize/url`   | Fetch + summarize a URL |
| `POST` | `/api/v1/summarize/pdf`   | Upload + summarize a PDF |
| `POST` | `/api/v1/summarize/batch` | Batch (multiple texts) |
| `POST` | `/api/v1/compare`         | Brief vs Detailed comparison |
| `POST` | `/api/v1/agent/run`       | Run autonomous AI agent |

---

## Project Structure

```
├── main.py                        # FastAPI entry point — serves SPA + API
├── frontend/
│   ├── index.html                 # Dark-mode SPA — all 5 tabs
│   └── static/
│       ├── css/style.css          # Full custom design system
│       └── js/
│           ├── api.js             # Fetch wrappers for all endpoints
│           └── app.js             # UI state, streaming, charts, agent steps
├── summarizer/
│   ├── core.py                    # Groq engine + domain-aware prompts + streaming
│   ├── ingestion.py               # PDF (pdfplumber) + URL (trafilatura)
│   ├── evaluation.py              # ROUGE scoring
│   └── config.py                  # pydantic-settings
├── api/
│   ├── routes.py                  # All FastAPI route handlers
│   └── schemas.py                 # Pydantic v2 request/response models
├── agent/
│   └── summarization_agent.py     # Autonomous agent: detect → select → summarize → evaluate
├── training/
│   ├── train.py                   # Seq2SeqTrainer fine-tuning script
│   └── evaluate.py                # Standalone ROUGE evaluation
├── tests/
│   ├── test_api.py                # Endpoint tests
│   └── test_core.py               # Unit tests for ingestion + evaluation
├── .github/workflows/
│   ├── ci.yml                     # pytest + ruff on Python 3.10 & 3.11
│   └── deploy.yml                 # Auto-deploy to HuggingFace Spaces
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

---

## ROUGE Benchmark (CNN/DailyMail test set, 100 samples)

| Model | ROUGE-1 | ROUGE-2 | ROUGE-L |
|-------|---------|---------|---------|
| `facebook/bart-large-cnn` (fine-tuned) | **0.442** | **0.213** | **0.410** |
| `sshleifer/distilbart-cnn-12-6` | 0.428 | 0.208 | 0.295 |
| `google/pegasus-cnn_dailymail` | 0.437 | 0.209 | 0.301 |
| `t5-base` | 0.371 | 0.155 | 0.265 |

---

## Author

**Karthik Mulugu**
[GitHub](https://github.com/Karthik0809) · [LinkedIn](https://www.linkedin.com/in/karthikmulugu/) · [Live Demo](https://huggingface.co/spaces/karthikmulugu08/text-summarizer)

---

## License

MIT — see [LICENSE](LICENSE) for details.
