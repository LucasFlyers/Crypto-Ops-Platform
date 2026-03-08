# ─── Builder stage ────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
        fastapi==0.111.0 \
        uvicorn[standard]==0.29.0 \
        sqlalchemy[asyncio]==2.0.30 \
        asyncpg==0.29.0 \
        alembic==1.13.1 \
        pydantic==2.7.1 \
        pydantic-settings==2.2.1 \
        celery[redis]==5.4.0 \
        redis==5.0.4 \
        openai==1.30.0 \
        structlog==24.2.0 \
        httpx==0.27.0 \
        tenacity==8.3.0 \
        python-dotenv==1.0.1 \
        psycopg2-binary==2.9.9 \
        streamlit==1.35.0 \
        pandas==2.2.2 \
        plotly==5.22.0 \
        requests==2.32.0

# ─── Runtime stage ─────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY app/ ./app/
COPY dashboard/ ./dashboard/
COPY alembic.ini .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]