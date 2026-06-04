"""Add device agents.

Revision ID: 20260604_0002
Revises: 20260604_0001
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa

revision = "20260604_0002"
down_revision = "20260604_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "device_agents" in inspector.get_table_names():
        return

    op.create_table(
        "device_agents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_device_agents_company_id", "device_agents", ["company_id"], unique=False)
    op.create_index("ix_device_agents_token_hash", "device_agents", ["token_hash"], unique=True)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "device_agents" not in inspector.get_table_names():
        return

    op.drop_index("ix_device_agents_token_hash", table_name="device_agents")
    op.drop_index("ix_device_agents_company_id", table_name="device_agents")
    op.drop_table("device_agents")
