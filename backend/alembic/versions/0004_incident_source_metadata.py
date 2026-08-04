"""Persist per-incident source metadata (vision source, LLM fields) for hazards."""

from alembic import op
import sqlalchemy as sa


revision = "0004_incident_source_metadata"
down_revision = "0003_knowledge_clause_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("incidents")}
    if "metadata_json" not in columns:
        op.add_column(
            "incidents",
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("incidents")}
    if "metadata_json" in columns:
        op.drop_column("incidents", "metadata_json")
