"""Persist article and effective date for source-backed knowledge clauses."""

from alembic import op
import sqlalchemy as sa


revision = "0003_knowledge_clause_metadata"
down_revision = "0002_result_payload_and_attachment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("knowledge_documents")}
    if "article" not in columns:
        op.add_column(
            "knowledge_documents",
            sa.Column("article", sa.String(length=128), nullable=False, server_default=sa.text("''")),
        )
    if "effective_date" not in columns:
        op.add_column("knowledge_documents", sa.Column("effective_date", sa.String(length=32), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("knowledge_documents")}
    if "effective_date" in columns:
        op.drop_column("knowledge_documents", "effective_date")
    if "article" in columns:
        op.drop_column("knowledge_documents", "article")
