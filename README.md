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

Production-grade abstractive text summarization powered by **Groq's Llama 3.3 70B**, with a custom dark-mode HTML/CSS/JS frontend, FastAPI REST backend, autonomous AI agent, real-time streaming, and multi-modal input — deployed to HuggingFace Spaces via Docker.

> **Live Demo →** [huggingface.co/spaces/karthikmulugu08/text-summarizer](https://huggingface.co/spaces/karthikmulugu08/text-summarizer)

---

## Features

| Feature | Details |
|---|---|
| **LLM Engine** | Groq API — Llama 3.3 70B; responses in under 2 s |
| **Domain-aware prompting** | General · News · Scientific · Technical · Finance · Dialogue |
| **Summary style** | Detailed (fact-preserving prose) or Brief (3-4 sentences) |
| **Multi-modal input** | Plain text · PDF upload (pdfplumber) · Web URL (trafilatura) |
| **Real-time streaming** | Token-by-token output via Groq streaming API |
| **AI Agent** | Auto domain detection → strategy selection → summarization → ROUGE-L quality check → auto-retry |
| **Batch processing** | Manual `---` separator or CSV upload; full-text CSV download |
| **ROUGE Evaluation** | ROUGE-1/2/L computed client-side in JS; radar chart + gauge bars |
| **Export** | TXT · JSON · Markdown |
| **History** | Session history persisted in `localStorage` |
| **Custom UI** | Vanilla HTML/CSS/JS dark-mode SPA — no UI framework |
| **REST API** | FastAPI with Swagger UI, Pydantic v2, CORS |
| **Docker** | Single-stage Dockerfile; runs on port 7860 |
| **CI/CD** | GitHub Actions → auto-deploy to HuggingFace Spaces |

---

## App Tabs

### Summarize
Paste text, drop a PDF, or enter a URL. Pick a domain and style, hit **Generate Summary**. Metrics (input words, output words, compression, latency) appear inline. Export the result as TXT, JSON, or Markdown.

### Compare
Run the same text through the **Brief** and **Detailed** prompt strategies side-by-side. A Canvas bar chart shows output length for each.

### Batch
Summarize up to 20 texts at once. Separate inputs with `---` or upload a CSV with a `text` column. Expandable per-row previews; download results as CSV.

### Evaluate
Paste any reference and generated summary to compute ROUGE-1, ROUGE-2, and ROUGE-L entirely in the browser — no server round-trip. Results display as gauge bars and a radar chart drawn on Canvas.

### AI Agent
Fully autonomous pipeline:
1. **Analyze** — counts words, detects domain, measures complexity
2. **Select strategy** — picks the optimal prompt style for the domain
3. **Summarize** — calls Llama 3.3 70B via Groq
4. **Evaluate** — scores quality with ROUGE-L; retries if below threshold

Displays a 4-step animated progress pipeline, confidence ring, and full text-analysis breakdown.

---

## Architecture

```
Input (Text / PDF / URL)
        │
        ▼
FastAPI REST  /api/v1          ◄──  Custom HTML/CSS/JS SPA
├── POST /summarize                 (frontend/index.html)
├── POST /summarize/url
├── POST /summarize/pdf
├── POST /summarize/batch
├── POST /compare
└── POST /agent/run
        │
        ▼
Groq API — Llama 3.3 70B Versatile
(domain-aware prompt · detailed / brief style)
        │
        ▼
SummaryResult {summary, input_tokens, output_tokens,
               compression_ratio, latency_ms}
```

---

## Quick Start

### Python (local)

```bash
git clone https://github.com/Karthik0809/Text-Summarization-LLM.git
cd Text-Summarization-LLM

pip install -r requirements.txt

# Add your Groq API key (free at console.groq.com)
cp .env.example .env
# GROQ_API_KEY=your_key_here

uvicorn main:app --reload --port 7860
# → http://localhost:7860
# → http://localhost:7860/api/docs  (Swagger UI)
```

### Docker

```bash
docker build -t text-summarizer .
docker run -p 7860:7860 -e GROQ_API_KEY=your_key text-summarizer
```

---

## REST API

Swagger UI available at `/api/docs`.

### Summarize text

```bash
curl -X POST http://localhost:7860/api/v1/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Scientists discovered...",
    "max_length": 200,
    "domain": "scientific",
    "style": "detailed"
  }'
```

```json
{
  "summary": "...",
  "model_id": "llama-3.3-70b-versatile",
  "input_tokens": 142,
  "output_tokens": 71,
  "compression_ratio": 2.0,
  "latency_ms": 820.3
}
```

### All endpoints

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
├── main.py                   # FastAPI entry point (serves SPA + API)
├── frontend/
│   ├── index.html            # Dark-mode SPA — all 5 tabs
│   └── static/
│       ├── css/style.css     # Full custom design system
│       └── js/
│           ├── api.js        # Fetch wrappers for all endpoints
│           └── app.js        # UI state, streaming, charts, agent steps
├── summarizer/
│   ├── core.py               # Groq engine + domain-aware prompts + streaming
│   ├── ingestion.py          # PDF (pdfplumber) + URL (trafilatura)
│   ├── evaluation.py         # ROUGE scoring
│   └── config.py             # pydantic-settings
├── api/
│   ├── routes.py             # All FastAPI endpoints
│   └── schemas.py            # Pydantic v2 request/response models
├── agent/
│   └── summarization_agent.py  # Autonomous agent: detect → select → summarize → evaluate
├── .github/workflows/
│   ├── ci.yml                # pytest + ruff
│   └── deploy.yml            # Auto-deploy to HuggingFace Spaces
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

---

## Deploy to HuggingFace Spaces

1. Create a Space (SDK: Docker, port 7860)
2. Add GitHub repo secrets:
   - `HF_TOKEN` — HuggingFace write token
   - `HF_USERNAME` — your HF username
3. Add Space secret: `GROQ_API_KEY`
4. Push to `main` → GitHub Actions auto-deploys

---

## Author

**Karthik Mulugu**
[GitHub](https://github.com/Karthik0809) · [LinkedIn](https://www.linkedin.com/in/karthikmulugu/) · [Live Demo](https://huggingface.co/spaces/karthikmulugu08/text-summarizer)

---

## License

MIT — see [LICENSE](LICENSE) for details.
