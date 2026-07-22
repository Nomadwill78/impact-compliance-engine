"""
FastAPI Application Entry Point
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router
from app.core.database import engine
from app.models import orm  # noqa: F401 — register ORM models


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator:
    from app.core.database import Base  # noqa: PLC0415
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[startup] Database tables verified / created.")
    yield
    await engine.dispose()
    print("[shutdown] Database engine disposed.")


def create_app() -> FastAPI:
    application = FastAPI(
        title="Impact Compliance Engine",
        description="Automated ESG/GRI/SASB compliance analysis for PDF, DOCX, XLSX, and TXT documents.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    application.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    application.include_router(router, prefix="/api/v1")

    @application.get("/health", tags=["system"], summary="Root health check")
    async def root_health() -> dict:
        return {"status": "ok", "service": "impact-compliance-engine", "version": "1.0.0"}

    return application


app = create_app()
