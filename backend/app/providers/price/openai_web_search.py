import json
import logging
from datetime import datetime

from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI

from app.providers.price.base import (
    PriceObservationResult,
    PriceProviderError,
    PriceProviderResult,
    PriceQuery,
)

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 90.0

# JSON Schema for OpenAI Structured Outputs (Responses API `text.format`).
# Every property must be listed in "required" under strict mode; optional
# values use a nullable type (["string", "null"]) instead of being omitted.
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "observations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_name": {"type": "string"},
                    "source_url": {"type": ["string", "null"]},
                    "observed_price": {"type": "number"},
                    "currency": {"type": "string"},
                    "market_region": {"type": "string", "enum": ["CHILE", "INTERNATIONAL"]},
                    "language": {"type": ["string", "null"]},
                    "observed_at": {"type": ["string", "null"]},
                    "matched_confidence": {"type": ["number", "null"]},
                },
                "required": [
                    "source_name",
                    "source_url",
                    "observed_price",
                    "currency",
                    "market_region",
                    "language",
                    "observed_at",
                    "matched_confidence",
                ],
                "additionalProperties": False,
            },
        },
        "notes": {"type": ["string", "null"]},
    },
    "required": ["observations", "notes"],
    "additionalProperties": False,
}


class OpenAIWebSearchProvider:
    """PriceProvider backed by the OpenAI Responses API with the web_search tool.

    OpenAI acts purely as a search/extraction/normalization step here: it must
    report prices exactly as found on real sources (never invent a price from
    its own trained knowledge, never convert currency itself). PriceService is
    the sole authority on which observations are valid, outlier detection,
    the final estimate, and market_scope.
    """

    name = "openai_web_search"

    def __init__(self, api_key: str, model: str, max_tool_calls: int) -> None:
        self._client = AsyncOpenAI(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS)
        self._model = model
        self._max_tool_calls = max_tool_calls

    async def get_price(self, query: PriceQuery) -> PriceProviderResult:
        prompt = self._build_prompt(query)
        logger.info(
            "Searching price for %s %s via OpenAI Web Search (model=%s)",
            query.name,
            query.collector_number,
            self._model,
        )

        try:
            response = await self._client.responses.create(
                model=self._model,
                tools=[{"type": "web_search"}],
                max_tool_calls=self._max_tool_calls,
                input=prompt,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "price_observations",
                        "schema": RESPONSE_SCHEMA,
                        "strict": True,
                    }
                },
            )
        except (APIConnectionError, APITimeoutError) as exc:
            logger.error("OpenAI request failed: %s", exc)
            raise PriceProviderError("Could not reach OpenAI") from exc
        except APIError as exc:
            logger.error("OpenAI API returned an error: %s", exc)
            raise PriceProviderError(f"OpenAI API error: {exc}") from exc

        logger.info("OpenAI Web Search completed (usage=%s)", response.usage)

        try:
            payload = json.loads(response.output_text)
        except (TypeError, ValueError) as exc:
            logger.error("OpenAI returned unparsable output: %s", exc)
            raise PriceProviderError("OpenAI returned an unparsable response") from exc

        raw_observations = payload.get("observations", [])
        observations = [self._to_observation(item) for item in raw_observations]
        logger.info("%d observation(s) extracted from OpenAI response", len(observations))
        return PriceProviderResult(observations=observations, notes=payload.get("notes"))

    @staticmethod
    def _build_prompt(query: PriceQuery) -> str:
        details = [f"Name: {query.name}", f"Collector number: {query.collector_number}"]
        if query.set_name:
            details.append(f"Set: {query.set_name}")
        if query.language:
            details.append(f"Language: {query.language}")
        details_block = "\n".join(f"- {d}" for d in details)

        return f"""You are a pricing research assistant for a personal Pokemon TCG card \
collection app focused on the CHILEAN market.

Card to price:
{details_block}

Instructions:
1. FIRST, specifically search Chilean sources: try "tcgmatch.cl" and other .cl Pokemon \
TCG stores/marketplaces, for this exact card (name + collector number + set, when known). \
This is the top priority.
2. AFTER that, if search budget remains, search international reference sources \
(TCGplayer, Cardmarket, PriceCharting, etc.) as a secondary fallback reference.
3. Report the price and currency EXACTLY as shown on the source page. Do NOT convert \
currency yourself, do NOT estimate exchange rates, do NOT guess a CLP-equivalent for a \
non-CLP source. Always report "currency" as an ISO 4217 code (e.g. "CLP", "USD", "EUR"), \
never a symbol like "$" -- infer the correct code from the site/context (e.g. a Chilean \
store's "$" means CLP, a US site's "$" means USD).
4. IMPORTANT: for each distinct source page, report ONLY ONE observation with a single \
representative price. If a page shows a range (e.g. min/market/max) for the SAME exact \
printing, use the "market" or average price -- do not create separate observations for \
min, market, and max of the same printing.
5. If a page shows prices for multiple language or print variants, report EACH variant \
as its own observation (do not silently pick one or drop the others) -- set "language" \
for each one accordingly (see point 11). If "Language" was specified above, still \
prioritize finding that exact variant, but keep reporting any other variant you come \
across too; PriceService will decide what to do with each, not you.
6. Set market_region to "CHILE" for Chilean stores/CLP prices, "INTERNATIONAL" otherwise.
7. Only include observations you actually found via search with a real source_url. Never \
fabricate a price or a source -- you are a researcher here, not the source of the price.
8. If you cannot find this exact printing (same collector number and set), do not \
silently substitute a different printing's price -- explain in "notes" instead.
9. Assume the card is in good / Near Mint condition unless a source clearly states \
otherwise.
10. Set matched_confidence (0.0-1.0) for how confident you are that each source is \
describing this exact card printing, not a different one.
11. Set "language" to the language/print variant of the SPECIFIC listing (e.g. "ES", \
"EN", "JP", or the language name if a code is unclear), whenever the source page lets \
you tell it apart (explicit language field, product title, card text visible in an \
image, etc). If you cannot tell, set it to null -- never guess.
"""

    @staticmethod
    def _to_observation(item: dict) -> PriceObservationResult:
        return PriceObservationResult(
            source_name=item["source_name"],
            source_url=item.get("source_url"),
            observed_price=item["observed_price"],
            currency=item["currency"],
            market_region=item["market_region"],
            language=item.get("language"),
            observed_at=_parse_observed_at(item.get("observed_at")),
            matched_confidence=item.get("matched_confidence"),
        )


def _parse_observed_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Could not parse observed_at value %r, ignoring it", value)
        return None
