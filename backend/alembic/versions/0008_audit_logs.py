"""Create audit_logs for the permission audit (audit) module.

权限审计：为审计日志建表（此前仅靠 create_all 建表、无迁移）。列与
app/models/entities.py 的 AuditLog 完全对齐，含 user_id+created_at 索引。
新表，幂等守卫。表在 seed/init 的 create_all 已建时直接跳过。
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_audit_logs"
down_revision = "0007_wellbeing_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "audit_logs" in tables:
        return
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("detail_json", sa.JSON(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_user_created", "audit_logs", ["user_id", "created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "audit_logs" not in tables:
        return
    op.drop_index("ix_audit_logs_user_created", table_name="audit_logs")
    op.drop_table("audit_logs")
