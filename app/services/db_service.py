"""
Async Database CRUD Service
"""

from __future__ import annotations

import json
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.orm import ComplianceReportORM, DocumentORM, FindingORM
from app.models.schemas import (
    AnalyticsSummary, AnomalyFinding, ComplianceReport, ComplianceScore,
    FileType, ParsedDocument, ReportListItem, Severity,
)


async def save_report(session: AsyncSession, report: ComplianceReport) -> None:
    doc = report.parsed
    session.add(DocumentORM(
        id=doc.document_id, filename=doc.filename, file_type=doc.file_type.value,
        page_count=doc.page_count, entity_count=len(doc.entities),
        section_count=len(doc.sections), table_count=len(doc.tables),
        raw_text=doc.raw_text[:50_000], parse_warnings=json.dumps(doc.warnings),
        parse_duration_ms=doc.parse_duration_ms,
    ))
    score = report.score
    session.add(ComplianceReportORM(
        id=report.report_id, document_id=doc.document_id,
        overall_score=score.overall, esg_score=score.esg,
        financial_score=score.financial, disclosure_score=score.disclosure,
        critical_count=score.critical_count, high_count=score.high_count,
        medium_count=score.medium_count, low_count=score.low_count, info_count=score.info_count,
        frameworks_applied=", ".join(report.frameworks_applied),
        llm_gap_summary=report.llm_gap_summary, analysis_duration_ms=report.analysis_duration_ms,
    ))
    for f in report.findings:
        session.add(FindingORM(
            id=f.finding_id, report_id=report.report_id, rule_id=f.rule_id,
            rule_name=f.rule_name, severity=f.severity.value, category=f.category,
            description=f.description, evidence=f.evidence,
            location=f.location, remediation=f.remediation,
        ))


async def get_report_by_id(session: AsyncSession, report_id: str) -> ComplianceReport | None:
    stmt = (select(ComplianceReportORM)
            .options(selectinload(ComplianceReportORM.findings), selectinload(ComplianceReportORM.document))
            .where(ComplianceReportORM.id == report_id))
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    return _to_schema(row)


async def list_reports(session: AsyncSession, limit: int = 20, offset: int = 0) -> list[ReportListItem]:
    stmt = (select(ComplianceReportORM).options(selectinload(ComplianceReportORM.document))
            .order_by(ComplianceReportORM.created_at.desc()).limit(limit).offset(offset))
    rows = (await session.execute(stmt)).scalars().all()
    return [ReportListItem(
        report_id=r.id, document_name=r.document.filename if r.document else "unknown",
        score=r.overall_score,
        finding_count=r.critical_count + r.high_count + r.medium_count + r.low_count + r.info_count,
        created_at=r.created_at,
    ) for r in rows]


async def get_analytics_summary(session: AsyncSession) -> AnalyticsSummary:
    doc_count = (await session.execute(select(func.count()).select_from(DocumentORM))).scalar() or 0
    if doc_count == 0:
        return AnalyticsSummary()
    agg = (await session.execute(select(
        func.count(ComplianceReportORM.id), func.avg(ComplianceReportORM.overall_score),
        func.sum(ComplianceReportORM.critical_count), func.sum(ComplianceReportORM.high_count),
    ))).one()
    total_findings = (await session.execute(select(func.count()).select_from(FindingORM))).scalar() or 0
    top = (await session.execute(
        select(FindingORM.rule_id, func.count(FindingORM.rule_id).label("f"))
        .group_by(FindingORM.rule_id).order_by(func.count(FindingORM.rule_id).desc()).limit(1)
    )).one_or_none()
    names = [r[0] for r in (await session.execute(
        select(DocumentORM.filename).order_by(DocumentORM.created_at.desc()).limit(50)
    )).all()]
    return AnalyticsSummary(
        total_documents=doc_count, total_findings=total_findings,
        critical_findings=int(agg[2] or 0), high_findings=int(agg[3] or 0),
        average_score=round(float(agg[1] or 0), 2),
        most_common_rule=top[0] if top else None, documents_processed=names,
    )


def _to_schema(row: ComplianceReportORM) -> ComplianceReport:
    d = row.document
    parsed = ParsedDocument(
        document_id=d.id, filename=d.filename,
        file_type=FileType(d.file_type) if d.file_type in FileType._value2member_map_ else FileType.UNKNOWN,
        page_count=d.page_count, raw_text=d.raw_text,
        parse_duration_ms=d.parse_duration_ms, warnings=json.loads(d.parse_warnings or "[]"),
    )
    findings = [AnomalyFinding(finding_id=f.id, rule_id=f.rule_id, rule_name=f.rule_name,
        severity=Severity(f.severity), category=f.category, description=f.description,
        evidence=f.evidence, location=f.location, remediation=f.remediation) for f in row.findings]
    score = ComplianceScore(overall=row.overall_score, esg=row.esg_score, financial=row.financial_score,
        disclosure=row.disclosure_score, critical_count=row.critical_count, high_count=row.high_count,
        medium_count=row.medium_count, low_count=row.low_count, info_count=row.info_count)
    return ComplianceReport(report_id=row.id, document_name=d.filename, parsed=parsed, findings=findings,
        score=score, frameworks_applied=row.frameworks_applied.split(", ") if row.frameworks_applied else [],
        llm_gap_summary=row.llm_gap_summary or "", created_at=row.created_at,
        analysis_duration_ms=row.analysis_duration_ms)
