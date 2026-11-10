"""
main.py — FastAPI application entry point

This file:
1. Creates the FastAPI app
2. Configures CORS (so the Next.js frontend can talk to it)
3. Mounts all API routers
4. Sets up the lifespan event to initialize the database on startup

Run with:
    uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.database import init_db
from app.api import auth, chat, memory, audit, approvals, workflows, briefing
from app.utils.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager — runs startup/shutdown logic.
    Replaces the deprecated @app.on_event("startup") pattern.
    """
    # ── Startup ───────────────────────────────────────────────
    logger.info("Personal AI Assistant backend starting up...")
    settings = get_settings()

    # Initialize database tables
    init_db()

    # Log configuration status
    if settings.gemini_configured:
        logger.info(f"Gemini configured: model={settings.gemini_model}")
    else:
        logger.warning("Gemini API key not set — AI responses will use placeholder mode.")

    if settings.google_oauth_configured:
        logger.info("Google OAuth configured.")
    else:
        logger.info("Google OAuth not configured — running in mock auth mode (Phase 1).")

    logger.info("Personal AI Assistant backend ready.")
    yield

    # ── Shutdown ──────────────────────────────────────────────
    logger.info("Personal AI Assistant backend shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Personal AI Assistant API",
        description="An Observable, Memory-Augmented Productivity Agent",
        version="0.1.0",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────
    # Allows Next.js frontend on localhost:3000 or 127.0.0.1:3000 to communicate
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            settings.frontend_url,
        ],
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(memory.router)
    app.include_router(audit.router)
    app.include_router(approvals.router)
    app.include_router(workflows.router)
    app.include_router(briefing.router)

    # ── Health check ──────────────────────────────────────────
    @app.get("/health", tags=["system"])
    def health():
        """
        Simple health check endpoint.
        Returns 200 OK when the backend is running.
        The frontend polls this on startup to confirm the backend is available.
        """
        settings = get_settings()
        return {
            "status": "ok",
            "service": "Personal AI Assistant",
            "version": "0.1.0",
            "gemini_configured": settings.gemini_configured,
            "gemini_model": settings.gemini_model if settings.gemini_configured else None,
            "google_oauth_configured": settings.google_oauth_configured,
        }

    return app


app = create_app()
