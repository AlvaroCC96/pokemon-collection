import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.card import Card
from app.schemas.stats import CardValueSummary, CollectionStatsResponse, CurrencyTotal
from app.services import price_service

logger = logging.getLogger(__name__)

TOP_VALUABLE_LIMIT = 5


def get_collection_stats(db: Session) -> CollectionStatsResponse:
    """Read-only, SQLite-only -- never touches a PriceProvider (no OpenAI cost).

    Uses each card's LATEST snapshot (via price_service.get_latest_snapshot_with_change,
    no duplicated logic). CLP is the only currency summed into total_estimated_value;
    any other currency is reported separately in other_currency_totals, never mixed in.
    """
    cards = db.query(Card).all()
    distinct_card_count = len(cards)
    total_card_count = sum(card.quantity for card in cards)

    clp_summaries: list[CardValueSummary] = []
    other_currency_totals: dict[str, list] = defaultdict(lambda: [0.0, 0])
    cards_with_valuation = 0
    last_price_update = None

    for card in cards:
        latest, change = price_service.get_latest_snapshot_with_change(db, card.id)
        if latest is None:
            continue

        cards_with_valuation += 1
        if last_price_update is None or latest.checked_at > last_price_update:
            last_price_update = latest.checked_at

        total_value = latest.estimated_price * card.quantity
        currency = latest.currency.upper()

        if currency == "CLP":
            clp_summaries.append(
                CardValueSummary(
                    card_id=card.id,
                    name=card.name,
                    collector_number=card.collector_number,
                    estimated_price=latest.estimated_price,
                    currency=latest.currency,
                    quantity=card.quantity,
                    total_value=round(total_value, 2),
                    market_scope=latest.market_scope,
                    checked_at=latest.checked_at,
                    price_change_percent=change.price_change_percent,
                )
            )
        else:
            bucket = other_currency_totals[currency]
            bucket[0] += total_value
            bucket[1] += 1

    cards_without_valuation = distinct_card_count - cards_with_valuation

    clp_summaries.sort(key=lambda summary: summary.total_value, reverse=True)
    total_estimated_value = round(sum(summary.total_value for summary in clp_summaries), 2)

    logger.info(
        "Collection stats: %d distinct cards, %d with valuation, %d without, "
        "total_estimated_value=%s CLP",
        distinct_card_count,
        cards_with_valuation,
        cards_without_valuation,
        total_estimated_value,
    )

    return CollectionStatsResponse(
        distinct_card_count=distinct_card_count,
        total_card_count=total_card_count,
        cards_with_valuation=cards_with_valuation,
        cards_without_valuation=cards_without_valuation,
        total_estimated_value=total_estimated_value,
        currency="CLP",
        other_currency_totals=[
            CurrencyTotal(currency=currency, total_value=round(values[0], 2), card_count=values[1])
            for currency, values in other_currency_totals.items()
        ],
        most_valuable_card=clp_summaries[0] if clp_summaries else None,
        top_valuable_cards=clp_summaries[:TOP_VALUABLE_LIMIT],
        last_price_update=last_price_update,
    )
