"""Create green assessment / env-record / target tables.

绿色建造扩展 Phase 1：新建三张表
- green_assessments：四节一环保评估（五维评分 → 总分 + 等级 + 报告预览）
- green_env_records：环保监测台账（扬尘/噪声/污水/固废读数 + 超标提醒），项目+日期唯一（当日可重录幂等）
- green_targets：项目碳排强度目标（tCO2e/m²，一项目一行）

每张表均有幂等守卫，兼容 metadata create_all 建的库。
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_green_assessment_env_target"
down_revision = "0009_schema_alignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if "green_assessments" not in tables:
        op.create_table(
            "green_assessments",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("project_id", sa.String(length=64), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("requested_by", sa.String(length=64), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("area_m2", sa.Float(), nullable=True),
            sa.Column("total_score", sa.Float(), nullable=True),
            sa.Column("level", sa.String(length=16), nullable=True),
            sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("report_preview", sa.Text(), nullable=False),
            sa.Column("result_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "green_env_records" not in tables:
        op.create_table(
            "green_env_records",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("project_id", sa.String(length=64), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("requested_by", sa.String(length=64), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("record_date", sa.Date(), nullable=False),
            sa.Column("pm25", sa.Float(), nullable=True),
            sa.Column("pm10", sa.Float(), nullable=True),
            sa.Column("tsp", sa.Float(), nullable=True),
            sa.Column("noise_day_db", sa.Float(), nullable=True),
            sa.Column("noise_night_db", sa.Float(), nullable=True),
            sa.Column("cod_mg", sa.Float(), nullable=True),
            sa.Column("ss_mg", sa.Float(), nullable=True),
            sa.Column("ph", sa.Float(), nullable=True),
            sa.Column("solid_waste_t", sa.Float(), nullable=True),
            sa.Column("alerts_json", sa.JSON(), nullable=False),
            sa.Column("has_alerts", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("result_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("project_id", "record_date", name="uq_green_env_record_project_date"),
        )
        op.create_index("ix_green_env_records_project_date", "green_env_records", ["project_id", "record_date"])

    if "green_targets" not in tables:
        op.create_table(
            "green_targets",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("project_id", sa.String(length=64), sa.ForeignKey("projects.id"), nullable=False, unique=True),
            sa.Column("target_intensity", sa.Float(), nullable=True),
            sa.Column("note", sa.Text(), nullable=False),
            sa.Column("created_by", sa.String(length=64), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    for table in ("green_targets", "green_env_records", "green_assessments"):
        if table in tables:
            op.drop_table(table)
