"""
Pydantic v2 Data Validation Models
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    TXT = "txt"
    UNKNOWN = "unknown"


class GRIStatus(str, Enum):
    DISCLOSED = "disclosed"
    PARTIAL = "partial"
    NOT_DISCLOSED = "not_disclosed"
    NOT_APPLICABLE = "not_applicable"


class ExtractedEntity(BaseModel):
    text: str
    label: str
    context: str = ""
    confidence: float | None = Field(None, ge=0.0, le=1.0)


class TableData(BaseModel):
    page_number: int | None = None
    sheet_name: str | None = None
    headers: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    row_count: int = 0


class NarrativeSection(BaseModel):
    heading: str
    body: str
    page_number: int | None = None
    word_count: int = 0


class ParsedDocument(BaseModel):
    document_id: str = Field(default_factory=lambda: str(uuid4()))
    filename: str
    file_type: FileType = FileType.PDF
    page_count: int = 0
    raw_text: str = ""
    entities: list[ExtractedEntity] = Field(default_factory=list)
    tables: list[TableData] = Field(default_factory=list)
    sections: list[NarrativeSection] = Field(default_factory=list)
    parse_duration_ms: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class GRIDisclosure(BaseModel):
    gri_id: str
    title: str
    status: GRIStatus = GRIStatus.NOT_DISCLOSED
    evidence: str = ""
    page_reference: str = ""


class SASBMetric(BaseModel):
    metric_id: str
    category: str
    description: str
    value_found: str = ""
    unit: str = ""
    status: GRIStatus = GRIStatus.NOT_DISCLOSED


class AnomalyFinding(BaseModel):
    finding_id: str = Field(default_factory=lambda: str(uuid4()))
    rule_id: str
    rule_name: str
    severity: Severity
    category: str
    description: str
    evidence: str = ""
    location: str = ""
    remediation: str = ""


class ComplianceScore(BaseModel):
    overall: float = Field(..., ge=0.0, le=100.0)
    esg: float = Field(100.0, ge=0.0, le=100.0)
    financial: float = Field(100.0, ge=0.0, le=100.0)
    disclosure: float = Field(100.0, ge=0.0, le=100.0)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0


class ComplianceReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    document_name: str
    parsed: ParsedDocument
    findings: list[AnomalyFinding] = Field(default_factory=list)
    gri_disclosures: list[GRIDisclosure] = Field(default_factory=list)
    sasb_metrics: list[SASBMetric] = Field(default_factory=list)
    score: ComplianceScore
    frameworks_applied: list[str] = Field(default_factory=list)
    llm_gap_summary: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    analysis_duration_ms: float = 0.0

    @property
    def has_critical(self) -> bool:
        return any(f.severity == Severity.CRITICAL for f in self.findings)


class UploadResponse(BaseModel):
    report_id: str
    document_name: str
    file_type: str
    page_count: int
    entity_count: int
    finding_count: int
    score: float
    gri_disclosed_count: int = 0
    message: str = "Document processed successfully."


class ReportListItem(BaseModel):
    report_id: str
    document_name: str
    score: float
    finding_count: int
    created_at: datetime


class AnalyticsSummary(BaseModel):
    total_documents: int = 0
    total_findings: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    average_score: float = 0.0
    most_common_rule: str | None = None
    documents_processed: list[str] = Field(default_factory=list)
