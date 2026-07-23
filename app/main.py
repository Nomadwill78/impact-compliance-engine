"""
FastAPI Application Entry Point
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router
from app.core.config import settings
from app.core.database import engine
from app.models import orm  # noqa: F401 — register ORM models

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator:
    if settings.USE_ALEMBIC_MIGRATIONS:
        logger.info("[startup] USE_ALEMBIC_MIGRATIONS=True — skipping auto create_all. Run `alembic upgrade head`.")
    else:
        from app.core.database import Base  # noqa: PLC0415

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.warning("[startup] Database tables auto-created via create_all (dev mode). "
                        "Set USE_ALEMBIC_MIGRATIONS=True and use Alembic for production schema management.")
    yield
    await engine.dispose()
    logger.info("[shutdown] Database engine disposed.")


def create_app() -> FastAPI:
    application = FastAPI(
        title="Impact Compliance Engine",
        description="Automated ESG/GRI/SASB compliance analysis for PDF, DOCX, XLSX, and TXT documents.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    cors_origins = settings.cors_origins_list
    if not cors_origins:
        logger.warning("[startup] CORS_ORIGINS is empty — no cross-origin requests will be allowed.")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
    )
    application.include_router(router, prefix="/api/v1")

    @application.get("/health", tags=["system"], summary="Root health check")
    async def root_health() -> dict:
        return {"status": "ok", "service": "impact-compliance-engine", "version": "1.0.0"}

    return application


app = create_app()
