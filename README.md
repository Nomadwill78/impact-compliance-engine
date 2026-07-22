# Impact Compliance Engine

A **FastAPI backend** for automated compliance analysis of PDF, DOCX, XLSX, and TXT documents against **GRI / SASB / ESG** frameworks, powered by **Google Gemini** for NLP and **PostgreSQL** for persistent storage.

---

## Features

| Capability | Details |
|---|---|
| 📄 **Multi-Format Ingestion** | PDF, DOCX, XLSX, TXT upload via REST API |
| 🔍 **Content Extraction** | Text, tables, and narrative sections from all formats |
| 🧠 **Gemini NLP** | Entity extraction + GRI/SASB compliance gap assessment |
| ⚖️ **16 Compliance Rules** | GRI Universal, GRI Topic Standards, SASB, ESG pillars |
| 📊 **GRI Disclosure Mapping** | Status per GRI standard (Disclosed / Partial / Not Disclosed) |
| 🎯 **Weighted Scoring** | Severity-based score 0–100 with ESG/Financial/Disclosure breakdown |
| 🐘 **PostgreSQL Storage** | Async SQLAlchemy — documents, reports, findings persisted |
| 📈 **Analytics API** | SQL-aggregated session-wide statistics |

---

## Compliance Rules

| Rule ID | Standard | Severity | Description |
|---|---|---|---|
| GRI-2-1 | GRI Universal | Medium | Organizational details disclosure |
| GRI-2-22 | GRI Universal | Medium | Senior leader sustainability statement |
| GRI-3-3 | GRI Universal | High | Materiality assessment |
| GRI-305-1 | GRI Emissions | High | Scope 1 & 2 GHG (quantified tCO2e) |
| GRI-305-3 | GRI Emissions | Medium | Scope 3 value chain emissions |
| GRI-303 | GRI Water | Medium | Water withdrawal by source |
| GRI-401 | GRI Social | Medium | New hires & employee turnover |
| GRI-416 | GRI Social | Low | Customer health & safety |
| SASB-ENE | SASB Environmental | Medium | Total energy consumption |
| SASB-WST | SASB Environmental | Low | Waste generation & diversion |
| ESG-GOV-001 | ESG Governance | High | Board composition & ethics |
| ESG-TGT-001 | ESG Environmental | Medium | Net-zero / SBTi targets |
| FIN-001 | Financial | **Critical** | Revenue figure inconsistency |
| FIN-002 | Financial | High | Percentage breakdown ≠ 100% |
| DIS-001 | Disclosure | High | Missing auditor/assurance |
| DIS-002 | Disclosure | Low | Missing FLS disclaimer |

---

## Setup

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — fill in GEMINI_API_KEY and DATABASE_URL
```

### 4. Create PostgreSQL database

```sql
CREATE DATABASE compliance_db;
```

### 5. Run database migrations

```bash
alembic upgrade head
```

> **Note**: The app also auto-creates tables on startup via SQLAlchemy (`Base.metadata.create_all`), so Alembic is optional for local development.

### 6. Start the server

```bash
uvicorn app.main:app --reload
```

API docs: **http://localhost:8000/docs**

---

## API Reference

### `POST /api/v1/upload`
Upload a document (PDF / DOCX / XLSX / TXT) for compliance analysis.

**Request**: `multipart/form-data` with field `file`

**Response**:
```json
{
  "report_id": "uuid",
  "document_name": "esg_report.pdf",
  "file_type": "pdf",
  "page_count": 24,
  "entity_count": 58,
  "finding_count": 4,
  "score": 62.0,
  "gri_disclosed_count": 5,
  "message": "Document processed successfully."
}
```

---

### `GET /api/v1/reports`
Paginated list of all reports.

Query params: `limit` (1–100, default 20), `offset` (default 0)

---

### `GET /api/v1/reports/{report_id}`
Full report: findings, GRI disclosures, SASB metrics, scores, Gemini gap summary.

---

### `GET /api/v1/analytics/summary`
SQL-aggregated session statistics:
```json
{
  "total_documents": 12,
  "total_findings": 47,
  "critical_findings": 2,
  "high_findings": 18,
  "average_score": 64.3,
  "most_common_rule": "GRI-305-1",
  "documents_processed": ["report_2024.pdf", "esg_annual.docx"]
}
```

---

## Running Tests

```bash
python -m pytest app/tests/test_ingest.py -v --asyncio-mode=auto
```

> Tests use an in-memory SQLite database and mock the Gemini API — no real credentials required.

---

## Project Structure

```
impact-compliance-engine/
├── app/
│   ├── main.py                  # FastAPI app factory + DB lifespan
│   ├── core/
│   │   ├── config.py            # Pydantic settings (env vars)
│   │   └── database.py          # Async SQLAlchemy engine + session
│   ├── api/
│   │   └── endpoints.py         # Upload, reports, analytics routes
│   ├── services/
│   │   ├── parser.py            # Multi-format document parser
│   │   ├── llm.py               # Google Gemini NLP service
│   │   ├── compliance.py        # GRI/SASB rule engine
│   │   └── db_service.py        # Async CRUD operations
│   ├── models/
│   │   ├── schemas.py           # Pydantic v2 models
│   │   └── orm.py               # SQLAlchemy ORM models
│   └── tests/
│       └── test_ingest.py       # Pytest suite
├── alembic/
│   ├── env.py                   # Async Alembic config
│   └── versions/001_initial.py  # Initial schema migration
├── alembic.ini
├── requirements.txt
└── .env.example
```

---

## Extending the Rule Engine

Add a rule in [`compliance.py`](app/services/compliance.py):

```python
def _my_rule(doc: ParsedDocument) -> list[AnomalyFinding]:
    if "required disclosure" not in doc.raw_text.lower():
        return [AnomalyFinding(
            rule_id="CUS-001",
            rule_name="My Custom Rule",
            severity=Severity.MEDIUM,
            category="Custom",
            description="Required disclosure missing.",
            remediation="Add the disclosure."
        )]
    return []
```

Then register it in `RuleEngine._load_rules()`.

---

## Contact & Author

- **GitHub**: [Nomadwill78](https://github.com/Nomadwill78)
- **Email**: nomadconsulting7@gmail.com

