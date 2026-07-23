"""initial schema: documents, compliance_reports, findings

Revision ID: 0001_initial_schema
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("file_type", sa.String(length=16), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("entity_count", sa.Integer(), nullable=False),
        sa.Column("section_count", sa.Integer(), nullable=False),
        sa.Column("table_count", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("parse_warnings", sa.Text(), nullable=False),
        sa.Column("parse_duration_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "compliance_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("esg_score", sa.Float(), nullable=False),
        sa.Column("financial_score", sa.Float(), nullable=False),
        sa.Column("disclosure_score", sa.Float(), nullable=False),
        sa.Column("critical_count", sa.Integer(), nullable=False),
        sa.Column("high_count", sa.Integer(), nullable=False),
        sa.Column("medium_count", sa.Integer(), nullable=False),
        sa.Column("low_count", sa.Integer(), nullable=False),
        sa.Column("info_count", sa.Integer(), nullable=False),
        sa.Column("frameworks_applied", sa.String(length=512), nullable=False),
        sa.Column("llm_gap_summary", sa.Text(), nullable=False),
        sa.Column("analysis_duration_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "findings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("report_id", sa.String(length=36), nullable=False),
        sa.Column("rule_id", sa.String(length=32), nullable=False),
        sa.Column("rule_name", sa.String(length=256), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("location", sa.Text(), nullable=False),
        sa.Column("remediation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["compliance_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_findings_rule_id"), "findings", ["rule_id"])
    op.create_index(op.f("ix_findings_severity"), "findings", ["severity"])
    op.create_index(op.f("ix_findings_category"), "findings", ["category"])


def downgrade() -> None:
    op.drop_index(op.f("ix_findings_category"), table_name="findings")
    op.drop_index(op.f("ix_findings_severity"), table_name="findings")
    op.drop_index(op.f("ix_findings_rule_id"), table_name="findings")
    op.drop_table("findings")
    op.drop_table("compliance_reports")
    op.drop_table("documents")
