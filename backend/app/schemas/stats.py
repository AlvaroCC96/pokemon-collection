from datetime import datetime

from pydantic import BaseModel


class CardValueSummary(BaseModel):
    card_id: int
    name: str
    collector_number: str
    estimated_price: float
    currency: str
    quantity: int
    total_value: float
    market_scope: str
    checked_at: datetime
    price_change_percent: float | None = None


class CurrencyTotal(BaseModel):
    currency: str
    total_value: float
    card_count: int


class CollectionStatsResponse(BaseModel):
    distinct_card_count: int
    total_card_count: int
    cards_with_valuation: int
    cards_without_valuation: int
    total_estimated_value: float
    currency: str
    other_currency_totals: list[CurrencyTotal]
    most_valuable_card: CardValueSummary | None
    top_valuable_cards: list[CardValueSummary]
    last_price_update: datetime | None
