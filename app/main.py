"""
app/main.py
────────────
FastAPI application factory.
Configures: middleware, routers, lifecycle hooks, error handlers.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.db.session import init_db, close_db
from app.utils.logging import configure_logging, get_logger
from app.api.v1 import tickets, fraud, dashboard

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    Handles startup and shutdown events cleanly.
    """
    # ── Startup ───────────────────────────────────────────────────
    logger.info(
        "application_starting",
        env=settings.app_env,
        host=settings.app_host,
        port=settings.app_port,
    )

    # Verify DB connection (don't create tables — Alembic handles that)
    try:
        from sqlalchemy import text
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        logger.info("database_connection_verified")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        # Don't crash on startup — let health check expose the issue

    yield

    # ── Shutdown ──────────────────────────────────────────────────
    logger.info("application_shutting_down")
    await close_db()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Crypto Operations & Risk Automation Platform",
        description=(
            "AI-powered internal operations platform for crypto exchange "
            "operational event management, fraud detection, and team routing."
        ),
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else ["https://your-internal-domain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request logging middleware ─────────────────────────────────
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            path=request.url.path,
            method=request.method,
        )
        response = await call_next(request)
        logger.info(
            "http_request",
            status_code=response.status_code,
        )
        return response

    # ── Error handlers ────────────────────────────────────────────
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        logger.warning(
            "request_validation_error",
            errors=exc.errors(),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "detail": exc.errors(),
                "message": "Request validation failed — check your input data",
            },
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            error=str(exc),
            path=request.url.path,
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
            },
        )

    # ── Routers ───────────────────────────────────────────────────
    app.include_router(tickets.router, prefix="/api/v1")
    app.include_router(fraud.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1")

    # ── Health check ──────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "env": settings.app_env,
            "version": "1.0.0",
        }

    @app.get("/", tags=["Health"])
    async def root():
        return {
            "service": "Crypto Operations & Risk Automation Platform",
            "version": "1.0.0",
            "docs": "/docs",
        }

    return app


app = create_application()
