from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel

MarketRegion = Literal["CHILE", "INTERNATIONAL"]


class PriceQuery(BaseModel):
    name: str
    collector_number: str
    set_name: str | None = None
    language: str | None = None


class PriceObservationResult(BaseModel):
    source_name: str
    source_url: str | None = None
    observed_price: float
    currency: str
    market_region: MarketRegion
    language: str | None = None  # language/print variant detected on the source, if identifiable
    observed_at: datetime | None = None
    matched_confidence: float | None = None


class PriceProviderResult(BaseModel):
    observations: list[PriceObservationResult]
    notes: str | None = None


class PriceProviderError(Exception):
    """Raised when a price provider cannot be reached or returns an unusable response."""


class PriceProvider(Protocol):
    name: str

    async def get_price(self, query: PriceQuery) -> PriceProviderResult: ...
