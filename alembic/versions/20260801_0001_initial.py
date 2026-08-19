"""Create initial macroeconomic data tables.

Revision ID: 20260801_0001
Revises:
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "economic_series",
        sa.Column("series_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("units", sa.String(length=255), nullable=True),
        sa.Column("frequency", sa.String(length=100), nullable=True),
        sa.Column("seasonal_adjustment", sa.String(length=255), nullable=True),
        sa.Column("observation_start", sa.Date(), nullable=True),
        sa.Column("observation_end", sa.Date(), nullable=True),
        sa.Column("last_updated_at_source", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("series_id"),
    )
    op.create_index("ix_economic_series_category", "economic_series", ["category"])
    op.create_index("ix_economic_series_display_name", "economic_series", ["display_name"])
    op.create_index("ix_economic_series_enabled", "economic_series", ["enabled"])
    op.create_index("ix_economic_series_source", "economic_series", ["source"])

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("series_requested", sa.Integer(), nullable=False),
        sa.Column("series_succeeded", sa.Integer(), nullable=False),
        sa.Column("observations_inserted", sa.Integer(), nullable=False),
        sa.Column("observations_updated", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_runs_status", "ingestion_runs", ["status"])

    op.create_table(
        "observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("series_id", sa.String(length=64), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("realtime_start", sa.Date(), nullable=True),
        sa.Column("realtime_end", sa.Date(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["series_id"], ["economic_series.series_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series_id", "observation_date", name="uq_observation_series_date"),
    )
    op.create_index("ix_observations_observation_date", "observations", ["observation_date"])
    op.create_index(
        "ix_observations_series_date", "observations", ["series_id", "observation_date"]
    )
    op.create_index("ix_observations_series_id", "observations", ["series_id"])

    op.create_table(
        "observation_revisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("series_id", sa.String(length=64), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("old_value", sa.Float(), nullable=True),
        sa.Column("new_value", sa.Float(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["series_id"], ["economic_series.series_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_observation_revisions_observation_date", "observation_revisions", ["observation_date"]
    )
    op.create_index("ix_observation_revisions_series_id", "observation_revisions", ["series_id"])
    op.create_index(
        "ix_revision_series_date", "observation_revisions", ["series_id", "observation_date"]
    )


def downgrade() -> None:
    op.drop_table("observation_revisions")
    op.drop_table("observations")
    op.drop_table("ingestion_runs")
    op.drop_table("economic_series")
