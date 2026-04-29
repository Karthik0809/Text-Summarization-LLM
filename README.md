---
title: Text Summarization — AI Agent + Groq
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

Production-grade abstractive text summarization powered by **Groq's Llama 3.3 70B**, with a custom dark-mode HTML/CSS/JS SPA, FastAPI REST backend, autonomous AI agent, real-time streaming, and multi-modal input — deployed on HuggingFace Spaces via Docker.

---

## Features

| Feature | Details |
|---|---|
| **LLM Engine** | Groq API — Llama 3.3 70B; responses under 2 s |
| **Domain-aware prompting** | General · News · Scientific · Technical · Finance · Dialogue |
| **Summary style** | Detailed (fact-preserving prose) or Brief (3–4 sentences) |
| **Multi-modal input** | Plain text · PDF upload (pdfplumber) · Web URL (trafilatura) |
| **Real-time streaming** | Token-by-token output via Groq streaming API |
| **AI Agent** | Domain detection → strategy selection → summarize → ROUGE-L quality check → auto-retry |
| **Batch processing** | Manual `---` separator or CSV upload; full-text CSV download |
| **ROUGE Evaluation** | ROUGE-1/2/L computed client-side in vanilla JS; radar chart + gauge bars |
| **Export** | TXT · JSON · Markdown |
| **History** | Session history persisted in `localStorage` |
| **Custom UI** | Vanilla HTML/CSS/JS dark-mode SPA — no UI framework |
| **REST API** | FastAPI with Swagger UI, Pydantic v2, CORS |
| **Docker** | Single Dockerfile, runs on port 7860 |
| **CI/CD** | GitHub Actions → auto-deploy to HuggingFace Spaces |

---

## Five Feature Tabs

### Summarize
Pick a **domain** and **style** (Detailed or Brief). Input via text area, PDF drop-zone, or URL fetch. Toggle real-time streaming. Metrics (input/output words, compression ratio, latency) shown inline. Export as TXT, JSON, or Markdown.

### Compare
Run the same text through **Brief** and **Detailed** prompt strategies side-by-side. Canvas bar chart shows output length for each.

### Batch
Summarize multiple texts — separate with `---` or upload a CSV with a `text` column. Expandable per-row previews. Download results as CSV.

### Evaluate
ROUGE-1, ROUGE-2, and ROUGE-L computed **entirely in the browser** via a custom vanilla JS implementation — no server round-trip. Results shown as gauge bars and a Canvas radar chart.

### AI Agent
Autonomous 4-step pipeline:
1. **Analyze** — counts words, detects domain via keyword scoring, measures sentence complexity
2. **Select strategy** — picks prompt style and token budget for the detected domain
3. **Summarize** — calls Llama 3.3 70B via Groq
4. **Evaluate** — scores quality with ROUGE-L; retries with alternate strategy if below threshold

Displays an animated step tracker, SVG confidence ring, and full text-analysis breakdown.

---

## Architecture

```
Input (Text / PDF / URL)
        │
        ▼
FastAPI  /api/v1               ◄──  HTML/CSS/JS SPA  (frontend/)
├── POST /summarize
├── POST /summarize/url
├── POST /summarize/pdf
├── POST /summarize/batch
├── POST /compare
└── POST /agent/run
        │
        ▼
Groq API — Llama 3.3 70B Versatile
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
# set GROQ_API_KEY=your_key   (free at console.groq.com)

uvicorn main:app --reload --port 7860
# App  → http://localhost:7860
# Docs → http://localhost:7860/api/docs
```

### Docker

```bash
docker build -t text-summarizer .
docker run -p 7860:7860 -e GROQ_API_KEY=your_key text-summarizer
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
│       ├── css/style.css          # Custom design system
│       └── js/
│           ├── api.js             # Fetch wrappers for all endpoints
│           └── app.js             # UI state, streaming, canvas charts, agent steps
├── summarizer/
│   ├── core.py                    # Groq engine + domain prompts + streaming
│   ├── ingestion.py               # PDF (pdfplumber) + URL (trafilatura)
│   ├── evaluation.py              # Server-side ROUGE scoring
│   └── config.py                  # pydantic-settings
├── api/
│   ├── routes.py                  # All FastAPI route handlers
│   └── schemas.py                 # Pydantic v2 request/response models
├── agent/
│   └── summarization_agent.py     # Autonomous agent pipeline
├── .github/workflows/
│   ├── ci.yml                     # pytest + ruff on Python 3.10 & 3.11
│   └── deploy.yml                 # Auto-deploy to HuggingFace Spaces
├── Dockerfile
└── requirements.txt
```

---

## Author

**Karthik Mulugu**
[GitHub](https://github.com/Karthik0809) · [LinkedIn](https://www.linkedin.com/in/karthikmulugu/) · [Live Demo](https://huggingface.co/spaces/karthikmulugu08/text-summarizer)

---

## License

MIT — see [LICENSE](LICENSE) for details.
