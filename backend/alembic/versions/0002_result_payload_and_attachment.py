"""Persist complete analysis payloads for history and attachments."""

from alembic import op
import sqlalchemy as sa


revision = "0002_result_payload_and_attachment"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("agent_runs")}
    if "result_json" not in columns:
        op.add_column("agent_runs", sa.Column("result_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade() -> None:
    op.drop_column("agent_runs", "result_json")
