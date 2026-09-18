from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base


class CardPriceSnapshot(Base):
    """One valuation run for a card. Represents the RESULT: what PriceService
    computed, using whichever observations it decided were valid."""

    __tablename__ = "card_price_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), nullable=False, index=True)
    estimated_price: Mapped[float] = mapped_column(Float, nullable=False)
    low_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="CLP")
    market_scope: Mapped[str] = mapped_column(String, nullable=False)  # CHILE | INTERNATIONAL
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_label: Mapped[str] = mapped_column(String, nullable=False)  # HIGH | MEDIUM | LOW
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    card: Mapped["Card"] = relationship(back_populates="price_snapshots")  # noqa: F821
    observations: Mapped[list["PriceObservation"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class PriceObservation(Base):
    """A single piece of evidence found for a card, EXACTLY as reported by the
    provider. Every observation found is stored here, even ones excluded from
    the snapshot's final estimate (wrong market, wrong currency, or outlier) —
    this table is the full audit trail behind a snapshot's numbers."""

    __tablename__ = "price_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_price_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("card_price_snapshots.id"), nullable=False, index=True
    )
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    observed_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    market_region: Mapped[str] = mapped_column(String, nullable=False)  # CHILE | INTERNATIONAL
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_outlier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    included_in_estimate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    snapshot: Mapped["CardPriceSnapshot"] = relationship(back_populates="observations")
