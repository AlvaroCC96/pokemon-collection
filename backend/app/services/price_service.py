import asyncio
import logging
import statistics
from collections import Counter

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.language_codes import normalize_language_code
from app.models.card import Card
from app.models.price import CardPriceSnapshot, PriceObservation
from app.providers.price.base import (
    PriceObservationResult,
    PriceProvider,
    PriceProviderError,
    PriceQuery,
)
from app.providers.price.openai_web_search import OpenAIWebSearchProvider
from app.schemas.price import (
    CardPriceHistoryResponse,
    SnapshotResponse,
    SourceResponse,
    UpdateAllCardResult,
    UpdateAllResponse,
    UpdatePriceResponse,
    Valuation,
)
from app.services.card_service import get_card

logger = logging.getLogger(__name__)

# Outlier detection: a price outside [median * LOW_FACTOR, median * HIGH_FACTOR]
# within the group actually used for the estimate is excluded. Simple median +
# fixed-ratio bounds, per ARCHITECTURE.md ("evita algoritmos complejos").
OUTLIER_LOW_FACTOR = 0.4
OUTLIER_HIGH_FACTOR = 2.5


class PriceProviderNotConfiguredError(Exception):
    """Raised when OPENAI_API_KEY is missing and a price lookup is attempted."""


class PriceSearchFailedError(Exception):
    """Raised when no usable price evidence could be turned into a valuation.

    `user_message` is Spanish, specific, and safe to show directly in the API
    response -- the generic "no se pudo calcular un precio" was not helpful
    enough to tell a real failure (e.g. a language mismatch) from a search
    that genuinely found nothing.
    """

    def __init__(self, message: str, user_message: str | None = None) -> None:
        super().__init__(message)
        self.user_message = user_message or "No se pudo calcular un precio confiable para esta carta."


def get_price_provider() -> PriceProvider:
    """FastAPI dependency. Overridden in tests to avoid real network/API calls."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise PriceProviderNotConfiguredError(
            "OPENAI_API_KEY is not set. Add it to .env before updating prices."
        )
    return OpenAIWebSearchProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_price_model,
        max_tool_calls=settings.openai_price_max_tool_calls,
    )


def _select_market_group(
    observations: list[PriceObservationResult],
) -> tuple[str, list[PriceObservationResult]] | tuple[None, None]:
    chile = [o for o in observations if o.market_region == "CHILE"]
    if chile:
        return "CHILE", chile
    international = [o for o in observations if o.market_region == "INTERNATIONAL"]
    if international:
        return "INTERNATIONAL", international
    return None, None


def _select_currency_group(
    observations: list[PriceObservationResult],
) -> tuple[str, list[PriceObservationResult]]:
    counts = Counter(o.currency.strip().upper() for o in observations)
    dominant_currency = counts.most_common(1)[0][0]
    same_currency = [o for o in observations if o.currency.strip().upper() == dominant_currency]
    return dominant_currency, same_currency


def _language_matches(observation_language: str | None, query_language: str) -> bool:
    """Uses the shared canonical codes (app.core.language_codes) so a card's
    language matches the same way here as it does for identification
    routing -- e.g. "ZH-TW" and "ZH-CN" are recognized as distinct, never
    silently collapsed into one generic "Chinese" bucket (ETAPA 5.5)."""
    if not observation_language:
        return False

    obs_code = normalize_language_code(observation_language)
    query_code = normalize_language_code(query_language)
    if obs_code is not None and query_code is not None:
        return obs_code == query_code

    # One or both sides didn't match a known alias: fall back to raw
    # comparison so two identical unrecognized strings still count as a
    # match, without two DIFFERENT unrecognized strings colliding just
    # because both normalized to "unknown".
    return observation_language.strip().lower() == query_language.strip().lower()


def _select_language_group(
    observations: list[PriceObservationResult], query_language: str | None
) -> list[PriceObservationResult]:
    """When the card has a known language, keep observations that either match it
    or have no detected language (unknown, not confirmed to be a different print).
    Observations confirmed to be a DIFFERENT language are excluded from the
    calculation (but still saved for traceability by the caller).

    When the card has no language set, no filtering happens here — per current
    scope, we don't try to auto-infer/reconcile language variants.

    If every observation turns out to be a confirmed different language, this
    returns an empty list on purpose — the caller treats "no valid evidence
    left" as PRICE_SEARCH_FAILED rather than silently estimating from the
    wrong print."""
    if not query_language:
        return observations

    return [
        o for o in observations if o.language is None or _language_matches(o.language, query_language)
    ]


def _mark_outliers(prices: list[float]) -> list[bool]:
    """Returns, per price, whether it's an outlier relative to the group's median."""
    median = statistics.median(prices)
    if median <= 0:
        return [False] * len(prices)
    low_bound = median * OUTLIER_LOW_FACTOR
    high_bound = median * OUTLIER_HIGH_FACTOR
    return [not (low_bound <= p <= high_bound) for p in prices]


def _confidence_score(included: list[PriceObservationResult], market_scope: str) -> float:
    n = len(included)
    source_score = min(n / 3, 1.0) * 0.5

    prices = [o.observed_price for o in included]
    if n >= 2 and statistics.mean(prices) > 0:
        coefficient_of_variation = statistics.pstdev(prices) / statistics.mean(prices)
        dispersion_score = max(0.0, 0.3 - coefficient_of_variation * 0.3)
    else:
        dispersion_score = 0.15  # can't measure dispersion with a single source

    matched = [o.matched_confidence for o in included if o.matched_confidence is not None]
    match_score = (sum(matched) / len(matched)) * 0.2 if matched else 0.1

    score = source_score + dispersion_score + match_score
    if market_scope == "INTERNATIONAL":
        score *= 0.7  # not the target market, inherently less relevant

    return round(min(max(score, 0.0), 1.0), 2)


def _confidence_label(score: float) -> str:
    if score >= 0.7:
        return "HIGH"
    if score >= 0.4:
        return "MEDIUM"
    return "LOW"


def _round_price(value: float, currency: str) -> float:
    return round(value) if currency.upper() == "CLP" else round(value, 2)


class PriceChange(BaseModel):
    previous_price: float | None = None
    price_change: float | None = None
    price_change_percent: float | None = None


def _compute_price_change(current: float, previous: float | None, currency: str) -> PriceChange:
    """Only meaningful when `previous` comes from a snapshot with the SAME
    currency and market_scope as `current` -- callers are responsible for
    finding a compatible previous snapshot before calling this."""
    if previous is None or previous == 0:
        return PriceChange()
    change = current - previous
    percent = round((change / previous) * 100, 2)
    return PriceChange(
        previous_price=previous,
        price_change=_round_price(change, currency),
        price_change_percent=percent,
    )


def _find_previous_compatible_snapshot(
    snapshots_desc: list[CardPriceSnapshot], current: CardPriceSnapshot
) -> CardPriceSnapshot | None:
    """`snapshots_desc` must be ordered newest-first and include `current`.
    Compatible = same currency AND same market_scope, per ARCHITECTURE.md
    (never compare CLP vs USD, or a Chile-only estimate vs an international one)."""
    found_current = False
    for snapshot in snapshots_desc:
        if not found_current:
            if snapshot.id == current.id:
                found_current = True
            continue
        if snapshot.currency == current.currency and snapshot.market_scope == current.market_scope:
            return snapshot
    return None


def get_latest_snapshot_with_change(
    db: Session, card_id: int
) -> tuple[CardPriceSnapshot | None, PriceChange]:
    """Latest snapshot for a card plus its change vs. the most recent
    compatible (same currency + market_scope) snapshot before it, if any.
    Read-only, SQLite-only -- never touches a PriceProvider."""
    # id.desc() breaks ties for checked_at, which SQLite's CURRENT_TIMESTAMP
    # only resolves to the second -- two snapshots created within the same
    # second would otherwise sort in an undefined order.
    snapshots_desc = (
        db.query(CardPriceSnapshot)
        .filter(CardPriceSnapshot.card_id == card_id)
        .order_by(CardPriceSnapshot.checked_at.desc(), CardPriceSnapshot.id.desc())
        .all()
    )
    if not snapshots_desc:
        return None, PriceChange()

    latest = snapshots_desc[0]
    previous = _find_previous_compatible_snapshot(snapshots_desc, latest)
    change = _compute_price_change(
        latest.estimated_price, previous.estimated_price if previous else None, latest.currency
    )
    return latest, change


async def update_price(db: Session, card_id: int, provider: PriceProvider) -> UpdatePriceResponse:
    card = get_card(db, card_id)  # raises CardNotFoundError -> 404 in main.py

    query = PriceQuery(
        name=card.name,
        collector_number=card.collector_number,
        set_name=card.set_name,
        language=card.language,
    )
    logger.info("Searching price for %s %s (card_id=%s)", card.name, card.collector_number, card.id)

    result = await provider.get_price(query)  # PriceProviderError propagates -> 502 in main.py
    observations = result.observations
    logger.info("%d observation(s) found for card_id=%s", len(observations), card.id)

    if not observations:
        raise PriceSearchFailedError(
            "No price observations found",
            user_message="No se encontró ninguna referencia de precio para esta carta en la búsqueda web.",
        )

    market_scope, market_group = _select_market_group(observations)
    if not market_group:
        raise PriceSearchFailedError(
            "No observations matched a known market region",
            user_message="Se encontraron precios, pero ninguno indicaba claramente su mercado (Chile o Internacional).",
        )

    language_group = _select_language_group(market_group, query.language)
    if not language_group:
        raise PriceSearchFailedError(
            f"No observations matched the card's language ({query.language})",
            user_message=(
                f'Se encontraron precios, pero ninguno coincide con el idioma de la carta '
                f'("{query.language}"). Revisa que el idioma esté bien escrito o inténtalo '
                "sin idioma para no filtrar por él."
            ),
        )

    currency, calc_group = _select_currency_group(language_group)
    prices = [o.observed_price for o in calc_group]
    outlier_flags = _mark_outliers(prices)
    valid_prices = [p for p, is_outlier in zip(prices, outlier_flags) if not is_outlier]

    if not valid_prices:
        raise PriceSearchFailedError(
            "All observations were classified as outliers",
            user_message="Todas las referencias encontradas tenían precios muy dispares entre sí y se descartaron como atípicas.",
        )

    estimated = _round_price(statistics.median(valid_prices), currency)
    low = _round_price(min(valid_prices), currency)
    high = _round_price(max(valid_prices), currency)

    included_for_confidence = [
        o for o, is_outlier in zip(calc_group, outlier_flags) if not is_outlier
    ]
    confidence_score = _confidence_score(included_for_confidence, market_scope)
    confidence_label = _confidence_label(confidence_score)

    logger.info(
        "Normalization for card_id=%s: market_scope=%s currency=%s estimated=%s "
        "confidence=%s (%s) from %d/%d observation(s)",
        card.id,
        market_scope,
        currency,
        estimated,
        confidence_score,
        confidence_label,
        len(valid_prices),
        len(observations),
    )

    snapshot = CardPriceSnapshot(
        card_id=card.id,
        estimated_price=estimated,
        low_price=low,
        high_price=high,
        currency=currency,
        market_scope=market_scope,
        confidence_score=confidence_score,
        confidence_label=confidence_label,
        source_count=len(valid_prices),
        provider=provider.name,
    )
    db.add(snapshot)
    db.flush()  # assign snapshot.id before creating child observations

    calc_group_ids = {id(o) for o in calc_group}
    outlier_by_identity = {id(o): flag for o, flag in zip(calc_group, outlier_flags)}

    for observation in observations:
        is_in_calc_group = id(observation) in calc_group_ids
        is_outlier = outlier_by_identity.get(id(observation), False)
        db.add(
            PriceObservation(
                card_price_snapshot_id=snapshot.id,
                card_id=card.id,
                source_name=observation.source_name,
                source_url=observation.source_url,
                observed_price=observation.observed_price,
                currency=observation.currency,
                market_region=observation.market_region,
                language=observation.language,
                observed_at=observation.observed_at,
                is_outlier=is_in_calc_group and is_outlier,
                included_in_estimate=is_in_calc_group and not is_outlier,
            )
        )

    db.commit()
    db.refresh(card)
    db.refresh(snapshot)
    logger.info("Price snapshot saved for card_id=%s (snapshot_id=%s)", card.id, snapshot.id)

    return UpdatePriceResponse(
        card=card,
        valuation=Valuation(
            estimated=estimated,
            low=low,
            high=high,
            currency=currency,
            market_scope=market_scope,
            confidence_score=confidence_score,
            confidence_label=confidence_label,
        ),
        sources=[SourceResponse.model_validate(obs) for obs in snapshot.observations],
    )


def get_price_history(db: Session, card_id: int) -> CardPriceHistoryResponse:
    """Read-only, SQLite-only -- never touches a PriceProvider (no OpenAI cost)."""
    get_card(db, card_id)  # raises CardNotFoundError -> 404 in main.py

    # id.asc() breaks ties for checked_at (see get_latest_snapshot_with_change).
    snapshots = (
        db.query(CardPriceSnapshot)
        .filter(CardPriceSnapshot.card_id == card_id)
        .order_by(CardPriceSnapshot.checked_at.asc(), CardPriceSnapshot.id.asc())
        .all()
    )

    responses: list[SnapshotResponse] = []
    previous_by_key: dict[tuple[str, str], CardPriceSnapshot] = {}
    for snapshot in snapshots:
        key = (snapshot.currency, snapshot.market_scope)
        previous = previous_by_key.get(key)
        change = _compute_price_change(
            snapshot.estimated_price,
            previous.estimated_price if previous else None,
            snapshot.currency,
        )
        responses.append(
            SnapshotResponse(
                id=snapshot.id,
                estimated_price=snapshot.estimated_price,
                low_price=snapshot.low_price,
                high_price=snapshot.high_price,
                currency=snapshot.currency,
                market_scope=snapshot.market_scope,
                confidence_score=snapshot.confidence_score,
                confidence_label=snapshot.confidence_label,
                source_count=snapshot.source_count,
                provider=snapshot.provider,
                checked_at=snapshot.checked_at,
                previous_price=change.previous_price,
                price_change=change.price_change,
                price_change_percent=change.price_change_percent,
                observations=[SourceResponse.model_validate(o) for o in snapshot.observations],
            )
        )
        previous_by_key[key] = snapshot

    return CardPriceHistoryResponse(card_id=card_id, snapshots=responses)


def _error_code_for(exc: Exception) -> str:
    if isinstance(exc, PriceSearchFailedError):
        return "PRICE_SEARCH_FAILED"
    if isinstance(exc, PriceProviderError):
        return "PRICE_PROVIDER_ERROR"
    return "UNEXPECTED_ERROR"


async def update_all_prices(db: Session, provider: PriceProvider) -> UpdateAllResponse:
    """Updates every card's price using the SAME update_price() logic above --
    no duplicated search/normalization logic. Each card gets its own DB session
    (SQLAlchemy Session isn't safe to share across concurrent coroutines), and
    concurrency is capped by PRICE_UPDATE_CONCURRENCY to control cost/rate limits.
    A failing card is recorded and does not stop the rest."""
    settings = get_settings()
    concurrency = max(1, settings.price_update_concurrency)

    card_ids = [row[0] for row in db.query(Card.id).all()]
    total = len(card_ids)
    logger.info("update-all: starting for %d card(s), concurrency=%d", total, concurrency)

    semaphore = asyncio.Semaphore(concurrency)
    results: list[UpdateAllCardResult | None] = [None] * total

    async def process(index: int, card_id: int) -> None:
        async with semaphore:
            session = SessionLocal()
            try:
                await update_price(session, card_id, provider)
                results[index] = UpdateAllCardResult(card_id=card_id, status="updated")
                logger.info("update-all: card_id=%s updated", card_id)
            except Exception as exc:
                session.rollback()
                logger.error("update-all: card_id=%s failed: %s", card_id, exc)
                results[index] = UpdateAllCardResult(
                    card_id=card_id, status="failed", error=_error_code_for(exc)
                )
            finally:
                session.close()

    if card_ids:
        await asyncio.gather(*(process(i, cid) for i, cid in enumerate(card_ids)))

    final_results = [r for r in results if r is not None]
    updated = sum(1 for r in final_results if r.status == "updated")
    failed = total - updated
    logger.info("update-all: finished total=%d updated=%d failed=%d", total, updated, failed)

    return UpdateAllResponse(total=total, updated=updated, failed=failed, details=final_results)
