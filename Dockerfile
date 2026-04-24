# Multi-stage Dockerfile — build once, target api or app
# HuggingFace Spaces default target: app (port 7860)
FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ─── API stage (local use) ────────────────────────────────────────────────────
FROM base AS api
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ─── Streamlit stage — default for HuggingFace Spaces (port 7860) ─────────────
FROM base AS app
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:7860/_stcore/health || exit 1
CMD ["streamlit", "run", "app.py", \
     "--server.port=7860", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false", \
     "--server.enableXsrfProtection=false", "--server.enableCORS=false"]

# HuggingFace Spaces builds the last stage by default
FROM app AS final
