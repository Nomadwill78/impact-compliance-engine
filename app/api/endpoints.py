"""
API Endpoints — /api/v1
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.schemas import AnalyticsSummary, ComplianceReport, ReportListItem, UploadResponse
from app.services import db_service
from app.services.compliance import ComplianceChecker, RuleEngine
from app.services.llm import GeminiNLPService
from app.services.parser import DocumentParser

router = APIRouter()

_parser = DocumentParser()
_rule_engine = RuleEngine()
_checker = ComplianceChecker(_rule_engine)
_llm = GeminiNLPService()

_ALLOWED_EXT = {".pdf", ".docx", ".xlsx", ".txt"}
_ALLOWED_MIME = {
    "application/pdf", "application/x-pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain", "binary/octet-stream",
}


@router.get("/health", tags=["system"], summary="API liveness probe")
async def health_check() -> dict:
    return {"status": "ok", "rules_loaded": len(_rule_engine.rules), "supported_formats": list(_ALLOWED_EXT)}


@router.post("/upload", response_model=UploadResponse, tags=["compliance"],
             summary="Upload a document for compliance analysis")
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF, DOCX, XLSX, or TXT")],
    session: AsyncSession = Depends(get_db_session),
) -> UploadResponse:
    filename = file.filename or "unknown"
    content_type = file.content_type or ""
    ext = Path(filename).suffix.lower()

    if ext not in _ALLOWED_EXT and content_type not in _ALLOWED_MIME:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "unsupported_file_type",
                    "message": f"Unsupported '{ext}'. Accepted: {sorted(_ALLOWED_EXT)}",
                    "filename": filename})

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "empty_file", "message": "Uploaded file is empty."})

    t0 = time.perf_counter()

    try:
        parsed_doc = _parser.parse(file_bytes, filename, content_type)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "parse_failure", "message": str(exc)}) from exc

    # Gemini NLP enrichment
    llm_gap_summary = ""
    if parsed_doc.raw_text.strip():
        entities = await _llm.extract_entities(parsed_doc.raw_text)
        parsed_doc.entities = entities
        gap_result = await _llm.assess_compliance_gaps(parsed_doc.raw_text)
        llm_gap_summary = gap_result.get("gap_summary", "")

    findings, score, gri, sasb = _checker.check(parsed_doc)
    analysis_ms = (time.perf_counter() - t0) * 1000

    report = _checker.build_report(parsed_doc, findings, score, gri, sasb, llm_gap_summary, analysis_ms)
    await db_service.save_report(session, report)

    return UploadResponse(
        report_id=report.report_id, document_name=filename,
        file_type=parsed_doc.file_type.value, page_count=parsed_doc.page_count,
        entity_count=len(parsed_doc.entities), finding_count=len(findings),
        score=score.overall,
        gri_disclosed_count=sum(1 for d in gri if d.status.value == "disclosed"),
        message="Document processed — CRITICAL issues detected." if report.has_critical else "Document processed successfully.",
    )


@router.get("/reports", response_model=list[ReportListItem], tags=["compliance"],
            summary="List all compliance reports (paginated)")
async def list_reports_endpoint(
    limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[ReportListItem]:
    return await db_service.list_reports(session, limit=limit, offset=offset)


@router.get("/reports/{report_id}", response_model=ComplianceReport, tags=["compliance"],
            summary="Retrieve a full compliance report by ID")
async def get_report(report_id: str, session: AsyncSession = Depends(get_db_session)) -> ComplianceReport:
    report = await db_service.get_report_by_id(session, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "report_not_found", "message": f"No report for id '{report_id}'."})
    return report


@router.get("/analytics/summary", response_model=AnalyticsSummary, tags=["analytics"],
            summary="Aggregate compliance statistics")
async def analytics_summary(session: AsyncSession = Depends(get_db_session)) -> AnalyticsSummary:
    return await db_service.get_analytics_summary(session)
