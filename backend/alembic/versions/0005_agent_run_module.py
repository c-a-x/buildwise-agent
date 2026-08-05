"""Add AgentRun.module for quality/safety task isolation.

质量巡检任务与安全分析任务共用 agent_runs 表；新增 module 列（safety|quality），
既有行回填为 safety，保证安全历史/工单查询不串入质量任务。
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_agent_run_module"
down_revision = "0004_incident_source_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("agent_runs")}
    if "module" not in columns:
        op.add_column(
            "agent_runs",
            sa.Column("module", sa.String(length=20), nullable=False, server_default="safety"),
        )
    op.execute("UPDATE agent_runs SET module = 'safety' WHERE module IS NULL OR module = ''")


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("agent_runs")}
    if "module" in columns:
        op.drop_column("agent_runs", "module")
