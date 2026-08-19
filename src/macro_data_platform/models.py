from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from macro_data_platform.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class EconomicSeries(Base):
    __tablename__ = "economic_series"

    series_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_series_id: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    indicator_code: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    country_code: Mapped[str | None] = mapped_column(String(3), nullable=True, index=True)
    country_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(100), index=True)
    source: Mapped[str] = mapped_column(String(50), default="WORLD_BANK", index=True)
    units: Mapped[str | None] = mapped_column(String(255), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    observation_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    observation_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    observations: Mapped[list["Observation"]] = relationship(
        back_populates="series", cascade="all, delete-orphan"
    )


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint("series_id", "observation_date", name="uq_observation_series_date"),
        Index("ix_observations_series_date", "series_id", "observation_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[str] = mapped_column(
        ForeignKey("economic_series.series_id", ondelete="CASCADE"), index=True
    )
    observation_date: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    series: Mapped[EconomicSeries] = relationship(back_populates="observations")


class ObservationRevision(Base):
    __tablename__ = "observation_revisions"
    __table_args__ = (Index("ix_revision_series_date", "series_id", "observation_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[str] = mapped_column(
        ForeignKey("economic_series.series_id", ondelete="CASCADE"), index=True
    )
    observation_date: Mapped[date] = mapped_column(Date, index=True)
    old_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(50), default="WORLD_BANK", index=True)
    status: Mapped[str] = mapped_column(String(20), default=RunStatus.RUNNING.value, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    series_requested: Mapped[int] = mapped_column(Integer, default=0)
    series_succeeded: Mapped[int] = mapped_column(Integer, default=0)
    observations_inserted: Mapped[int] = mapped_column(Integer, default=0)
    observations_updated: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
