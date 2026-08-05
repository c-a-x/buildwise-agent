"""Extend carbon_analyses for the green carbon accounting core.

绿色碳排核算 Phase 1 把占位表 carbon_analyses 扩展为真实核算记录：
新增 requested_by / area_m2 / scope / is_simulated / report_preview / factor_version；
条目与分阶段明细写入 result_json，不建子表。既有行按默认值回填。
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_carbon_analysis_fields"
down_revision = "0005_agent_run_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("carbon_analyses")}
    additions = {
        "requested_by": sa.Column("requested_by", sa.String(length=64), nullable=True),
        "area_m2": sa.Column("area_m2", sa.Float(), nullable=True),
        "scope": sa.Column("scope", sa.Text(), nullable=False, server_default=""),
        "is_simulated": sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default="0"),
        "report_preview": sa.Column("report_preview", sa.Text(), nullable=False, server_default=""),
        "factor_version": sa.Column("factor_version", sa.String(length=64), nullable=False, server_default=""),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("carbon_analyses", column)


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("carbon_analyses")}
    for column in ("factor_version", "report_preview", "is_simulated", "scope", "area_m2", "requested_by"):
        if column in columns:
            op.drop_column("carbon_analyses", column)
