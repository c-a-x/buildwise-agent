"""Create wellbeing_records for the worker wellbeing (care) module.

工友关怀 Phase 1：新建 wellbeing_records 表保存天气/环境输入的高温关怀分析
（高温等级 / 体感温度 / 中暑风险指数 / 结果明细 result_json）。新表，幂等守卫。
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_wellbeing_records"
down_revision = "0006_carbon_analysis_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = {row[0] for row in sa.inspect(bind).get_table_names()}
    if "wellbeing_records" in tables:
        return
    op.create_table(
        "wellbeing_records",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("project_id", sa.String(length=64), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("requested_by", sa.String(length=64), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("heat_level", sa.String(length=16), nullable=False),
        sa.Column("heat_index", sa.Float(), nullable=True),
        sa.Column("risk_index", sa.Integer(), nullable=True),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    bind = op.get_bind()
    tables = {row[0] for row in sa.inspect(bind).get_table_names()}
    if "wellbeing_records" not in tables:
        return
    op.drop_table("wellbeing_records")
