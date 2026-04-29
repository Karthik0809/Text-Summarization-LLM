---
title: Advanced Text Summarization with BART
emoji: 🔬
colorFrom: blue
colorTo: indigo
sdk: streamlit
app_file: app.py
pinned: true
license: mit
---

# Text Summarization — LLM-Powered

[![CI](https://github.com/Karthik0809/Text-Summarization-Using-BART/actions/workflows/ci.yml/badge.svg)](https://github.com/Karthik0809/Text-Summarization-Using-BART/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Live Demo](https://img.shields.io/badge/🤗%20HF%20Spaces-Live%20Demo-orange)](https://huggingface.co/spaces/karthikmulugu08/text-summarizer)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](Dockerfile)

Production-grade abstractive text summarization powered by **Groq's Llama 3.3 70B** via a FastAPI REST backend, multi-modal input (text / PDF / URL), real-time token streaming, batch processing, and an interactive ROUGE evaluation dashboard — deployed to HuggingFace Spaces.

> **Live Demo →** [huggingface.co/spaces/karthikmulugu08/text-summarizer](https://huggingface.co/spaces/karthikmulugu08/text-summarizer)

---

## Features

| Feature | Details |
|---|---|
| **LLM Engine** | Groq API — Llama 3.3 70B Versatile; summaries in under 2 s |
| **Multi-modal input** | Plain text · PDF upload (pdfplumber) · Web URL (trafilatura) |
| **Streaming** | Real-time token-by-token output via Groq streaming API |
| **Domain-aware prompts** | Scientific · Technical · News · Finance · Dialogue modes |
| **Batch processing** | Up to 20 texts at once; CSV upload + download |
| **Evaluation dashboard** | ROUGE-1/2/L/Lsum gauge charts + radar chart (Plotly) |
| **Export** | Summary as TXT · JSON · Markdown |
| **REST API** | FastAPI with Swagger UI, Pydantic v2 validation, CORS |
| **Docker** | Multi-stage Dockerfile; `docker-compose` for API + UI |
| **CI/CD** | GitHub Actions → pytest + ruff + auto-deploy to HF Spaces |

---

## Architecture

```
Input Sources          Ingestion Layer         Engine
─────────────          ───────────────         ──────
Plain Text    ──────►  (direct)          ──►
PDF Upload    ──────►  pdfplumber        ──►  Groq Llama 3.3 70B
Web URL       ──────►  trafilatura       ──►  (domain-aware prompt)
                                              │
                                              ▼
                                         Summary + Metrics
                                              │
                        ┌─────────────────────┴─────────────────┐
                        │                                         │
                   Streamlit UI                           FastAPI /api/v1
                   ─────────────                         ──────────────────
                   Summarize tab                         POST /summarize
                   Compare tab                           POST /summarize/url
                   Batch tab                             POST /summarize/pdf
                   Evaluate tab (ROUGE)                  POST /summarize/batch
                   API Docs tab                          POST /compare
```

---

## Quick Start

### Option 1 — Python (local)

```bash
git clone https://github.com/Karthik0809/Text-Summarization-Using-BART.git
cd Text-Summarization-Using-BART
pip install -r requirements.txt

# Set your Groq API key (free at console.groq.com)
cp .env.example .env
# Add: GROQ_API_KEY=your_key_here

# Launch Streamlit UI
streamlit run app.py

# Or launch FastAPI backend
uvicorn api.main:app --reload
# → http://localhost:8000/docs
```

### Option 2 — Docker Compose

```bash
docker-compose up --build
# Streamlit → http://localhost:8501
# FastAPI   → http://localhost:8000/docs
```

### Option 3 — HuggingFace Spaces

Click the **Live Demo** badge above — no setup required.

---

## REST API

Interactive Swagger docs at `http://localhost:8000/docs`.

### Summarize text

```bash
curl -X POST http://localhost:8000/api/v1/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Scientists discovered a method for carbon capture...",
    "max_length": 150,
    "domain": "scientific"
  }'
```

```json
{
  "summary": "Scientists discovered a new carbon capture method...",
  "model_id": "llama-3.3-70b-versatile",
  "input_tokens": 128,
  "output_tokens": 64,
  "compression_ratio": 2.0,
  "latency_ms": 780.4
}
```

### All endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/v1/health`          | API status + loaded model |
| `GET`  | `/api/v1/models`          | List available models |
| `POST` | `/api/v1/summarize`       | Summarize plain text |
| `POST` | `/api/v1/summarize/url`   | Fetch + summarize a URL |
| `POST` | `/api/v1/summarize/pdf`   | Upload + summarize a PDF |
| `POST` | `/api/v1/summarize/batch` | Batch (up to 20 texts) |
| `POST` | `/api/v1/compare`         | Multi-model comparison |

---

## Project Structure

```
├── app.py                    # Streamlit UI (HF Spaces entry point)
├── summarizer/               # Core package
│   ├── core.py               # Groq engine + streaming + domain prompts
│   ├── ingestion.py          # PDF (pdfplumber) + URL (trafilatura)
│   ├── evaluation.py         # ROUGE + BERTScore metrics
│   └── config.py             # pydantic-settings configuration
├── api/                      # FastAPI backend
│   ├── main.py               # App + middleware
│   ├── routes.py             # All endpoints
│   └── schemas.py            # Pydantic v2 request/response models
├── training/
│   ├── train.py              # Fine-tuning scaffold (Seq2SeqTrainer)
│   └── evaluate.py           # Standalone ROUGE evaluation script
├── tests/
│   ├── test_api.py           # Endpoint tests (mocked engine)
│   └── test_core.py          # Unit tests for ingestion + evaluation
├── .github/workflows/
│   ├── ci.yml                # pytest + ruff on Python 3.10 & 3.11
│   └── deploy.yml            # Auto-deploy to HuggingFace Spaces
├── Dockerfile                # Multi-stage build
├── docker-compose.yml        # API + UI services
├── pyproject.toml            # Modern Python packaging + tool config
└── Makefile                  # Convenience targets
```

---

## Development

```bash
# Install dev dependencies
make dev

# Run tests
make test

# Lint
make lint

# Start API (watch mode)
make api

# Start Streamlit
make app
```

---

## Deploy to HuggingFace Spaces

1. Create a Space at [huggingface.co/new-space](https://huggingface.co/new-space) (SDK: Streamlit)
2. Add secrets to your GitHub repo:
   - `HF_TOKEN` — your HuggingFace write token
   - `HF_USERNAME` — your HuggingFace username
   - `GROQ_API_KEY` — your Groq API key (add in HF Space secrets too)
3. Push to `main` → GitHub Actions auto-deploys

---

## Author

**Karthik Mulugu**  
[GitHub](https://github.com/Karthik0809) · [LinkedIn](https://www.linkedin.com/in/karthikmulugu/) · [Live Demo](https://huggingface.co/spaces/karthikmulugu08/text-summarizer)

---

## License

MIT License — see [LICENSE](LICENSE) for details.
