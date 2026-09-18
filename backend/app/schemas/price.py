from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.card import CardResponse

MarketScope = Literal["CHILE", "INTERNATIONAL"]
ConfidenceLabel = Literal["HIGH", "MEDIUM", "LOW"]


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_name: str
    source_url: str | None
    observed_price: float
    currency: str
    market_region: str
    language: str | None
    observed_at: datetime | None
    is_outlier: bool
    included_in_estimate: bool


class Valuation(BaseModel):
    estimated: float
    low: float | None
    high: float | None
    currency: str
    market_scope: MarketScope
    confidence_score: float
    confidence_label: ConfidenceLabel


class UpdatePriceResponse(BaseModel):
    card: CardResponse
    valuation: Valuation
    sources: list[SourceResponse]


class SnapshotResponse(BaseModel):
    id: int
    estimated_price: float
    low_price: float | None
    high_price: float | None
    currency: str
    market_scope: MarketScope
    confidence_score: float
    confidence_label: ConfidenceLabel
    source_count: int
    provider: str
    checked_at: datetime
    previous_price: float | None
    price_change: float | None
    price_change_percent: float | None
    observations: list[SourceResponse]


class CardPriceHistoryResponse(BaseModel):
    card_id: int
    snapshots: list[SnapshotResponse]  # chronological order, oldest first


class UpdateAllCardResult(BaseModel):
    card_id: int
    status: Literal["updated", "failed"]
    error: str | None = None


class UpdateAllResponse(BaseModel):
    total: int
    updated: int
    failed: int
    details: list[UpdateAllCardResult]
