# ─── Builder stage ────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml .

# Install dependencies into a virtual env
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
        anthropic==0.28.0 \
        structlog==24.2.0 \
        httpx==0.27.0 \
        tenacity==8.3.0 \
        python-dotenv==1.0.1 \
        psycopg2-binary==2.9.9

# ─── Runtime stage ─────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system deps
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ ./app/
COPY alembic.ini .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
