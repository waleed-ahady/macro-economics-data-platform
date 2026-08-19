"""Add multi-country and provider metadata.

Revision ID: 20260818_0002
Revises: 20260801_0001
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260818_0002"
down_revision: str | None = "20260801_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("economic_series") as batch:
        batch.add_column(sa.Column("provider_series_id", sa.String(length=96), nullable=True))
        batch.add_column(sa.Column("indicator_code", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("country_code", sa.String(length=3), nullable=True))
        batch.add_column(sa.Column("country_name", sa.String(length=100), nullable=True))
        batch.create_index("ix_economic_series_provider_series_id", ["provider_series_id"])
        batch.create_index("ix_economic_series_indicator_code", ["indicator_code"])
        batch.create_index("ix_economic_series_country_code", ["country_code"])
        batch.create_index("ix_economic_series_country_name", ["country_name"])

    with op.batch_alter_table("ingestion_runs") as batch:
        batch.add_column(
            sa.Column("provider", sa.String(length=50), nullable=False, server_default="unknown")
        )
        batch.create_index("ix_ingestion_runs_provider", ["provider"])


def downgrade() -> None:
    with op.batch_alter_table("ingestion_runs") as batch:
        batch.drop_index("ix_ingestion_runs_provider")
        batch.drop_column("provider")

    with op.batch_alter_table("economic_series") as batch:
        batch.drop_index("ix_economic_series_country_name")
        batch.drop_index("ix_economic_series_country_code")
        batch.drop_index("ix_economic_series_indicator_code")
        batch.drop_index("ix_economic_series_provider_series_id")
        batch.drop_column("country_name")
        batch.drop_column("country_code")
        batch.drop_column("indicator_code")
        batch.drop_column("provider_series_id")
