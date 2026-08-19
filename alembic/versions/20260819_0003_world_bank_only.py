"""Simplify the schema for the World Bank-only platform.

Revision ID: 20260819_0003
Revises: 20260818_0002
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0003"
down_revision: str | None = "20260818_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Keep the persisted catalog aligned with the single-provider application.
    op.execute(sa.text("DELETE FROM economic_series WHERE source <> 'WORLD_BANK'"))

    with op.batch_alter_table("economic_series") as batch:
        batch.drop_column("seasonal_adjustment")
        batch.drop_column("last_updated_at_source")

    with op.batch_alter_table("observations") as batch:
        batch.drop_column("realtime_start")
        batch.drop_column("realtime_end")


def downgrade() -> None:
    with op.batch_alter_table("observations") as batch:
        batch.add_column(sa.Column("realtime_end", sa.Date(), nullable=True))
        batch.add_column(sa.Column("realtime_start", sa.Date(), nullable=True))

    with op.batch_alter_table("economic_series") as batch:
        batch.add_column(
            sa.Column("last_updated_at_source", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(sa.Column("seasonal_adjustment", sa.String(length=255), nullable=True))
