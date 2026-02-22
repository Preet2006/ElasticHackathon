# ═══════════════════════════════════════════════════════════════════════════════
# CodeJanitor 2.0 – Production Dockerfile
# Elasticsearch Agent Builder Hackathon
# ═══════════════════════════════════════════════════════════════════════════════
# LLM   : Groq  (llama-3.3-70b-versatile)
# KB    : Elasticsearch Cloud
# Sandbox: Docker-in-Docker via mounted /var/run/docker.sock
# ═══════════════════════════════════════════════════════════════════════════════

FROM python:3.11-slim AS base

# ── system deps ──────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        docker.io \
        curl \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps (cached layer) ──────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Application code ────────────────────────────────────────────────────────
COPY api.py .
COPY app/ ./app/

# ── Runtime ──────────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8000/"]

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
