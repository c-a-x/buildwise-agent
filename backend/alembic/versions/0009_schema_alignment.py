"""Align indexes and foreign keys introduced in the SQLAlchemy metadata.

The 0005 and 0006 migrations added the related column definitions, but older
databases can still be missing the metadata-level index and foreign key.  The
operations below are guarded so they are safe for databases created by either
the migration chain or ``Base.metadata.create_all``.
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_schema_alignment"
down_revision = "0008_audit_logs"
branch_labels = None
depends_on = None


def _has_requested_by_foreign_key(bind: sa.Connection) -> bool:
    foreign_keys = sa.inspect(bind).get_foreign_keys("carbon_analyses")
    return any(
        set(foreign_key.get("constrained_columns") or []) == {"requested_by"}
        and foreign_key.get("referred_table") == "users"
        and set(foreign_key.get("referred_columns") or []) == {"id"}
        for foreign_key in foreign_keys
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes("agent_runs")}
    if "ix_agent_runs_module" not in existing_indexes:
        op.create_index("ix_agent_runs_module", "agent_runs", ["module"])

    if _has_requested_by_foreign_key(bind):
        return

    invalid_references = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM carbon_analyses ca "
            "LEFT JOIN users u ON u.id = ca.requested_by "
            "WHERE ca.requested_by IS NOT NULL AND u.id IS NULL"
        )
    ).scalar_one()
    if invalid_references:
        raise RuntimeError(
            "Cannot add carbon_analyses.requested_by foreign key: "
            f"{invalid_references} row(s) reference missing users."
        )

    with op.batch_alter_table("carbon_analyses", recreate="always") as batch_op:
        batch_op.create_foreign_key(
            "fk_carbon_analyses_requested_by_users",
            "users",
            ["requested_by"],
            ["id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _has_requested_by_foreign_key(bind):
        with op.batch_alter_table("carbon_analyses", recreate="always") as batch_op:
            batch_op.drop_constraint(
                "fk_carbon_analyses_requested_by_users",
                type_="foreignkey",
            )

    existing_indexes = {index["name"] for index in inspector.get_indexes("agent_runs")}
    if "ix_agent_runs_module" in existing_indexes:
        op.drop_index("ix_agent_runs_module", table_name="agent_runs")
