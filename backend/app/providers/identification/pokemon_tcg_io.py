import asyncio
import logging

import httpx

from app.providers.identification.base import (
    IdentificationCandidate,
    IdentificationProviderError,
    IdentificationQuery,
    IdentificationResult,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.pokemontcg.io/v2/cards"
REQUEST_TIMEOUT_SECONDS = 10.0
PAGE_SIZE = 25

# pokemontcg.io es notoriamente inestable sin API key (500/502 intermitentes por
# límite de tasa compartido entre usuarios anónimos). Reintentamos unas pocas
# veces solo ante errores transitorios (5xx / red) antes de rendirnos.
MAX_ATTEMPTS = 4
RETRY_BACKOFF_SECONDS = 1.0


def _normalize_number(collector_number: str) -> str:
    """pokemontcg.io stores `number` without leading zeros ("74", not "074"),
    even for cards printed with them (secret rares like "074/073"). Strip
    them so the search matches -- but only leading zeros on an otherwise
    numeric string; an alphanumeric promo code (e.g. "SWSH261") is untouched
    since it doesn't start with "0"."""
    number = collector_number.split("/")[0].strip()
    return number.lstrip("0") or "0"


class PokemonTCGIOProvider:
    """IdentificationProvider backed by the public pokemontcg.io catalog.

    Note: pokemontcg.io does not track per-language card variants, so
    `language` is accepted on the query for forward-compatibility but is
    not used to filter results, and returned candidates never populate it.
    """

    name = "pokemon_tcg_io"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    async def find_candidates(self, query: IdentificationQuery) -> IdentificationResult:
        logger.info(
            "Querying pokemontcg.io for name=%r number=%r set=%r",
            query.name,
            query.collector_number,
            query.set_name,
        )

        items = await self._fetch(self._build_query(query, query.name))

        if not items:
            for variant in self._spacing_variants(query.name):
                logger.info("No match for name=%r, retrying with variant %r", query.name, variant)
                items = await self._fetch(self._build_query(query, variant))
                if items:
                    break

        candidates = [self._to_candidate(item) for item in items]
        logger.info("pokemontcg.io returned %d candidate(s)", len(candidates))
        # already filtered by number+set, so a single page is always exact
        return IdentificationResult(candidates=candidates, has_more=False)

    async def _fetch(self, query_string: str) -> list[dict]:
        params = {"q": query_string, "pageSize": PAGE_SIZE}
        headers = {"X-Api-Key": self._api_key} if self._api_key else {}

        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                    response = await client.get(BASE_URL, params=params, headers=headers)
            except httpx.RequestError as exc:
                last_error = exc
                logger.warning(
                    "pokemontcg.io request failed (attempt %d/%d): %s", attempt, MAX_ATTEMPTS, exc
                )
            else:
                if response.status_code == 200:
                    payload = response.json()
                    return payload.get("data", [])

                if response.status_code < 500:
                    # Client-side error (4xx): retrying won't help.
                    logger.error(
                        "pokemontcg.io returned status %s: %s",
                        response.status_code,
                        response.text[:200],
                    )
                    raise IdentificationProviderError(
                        f"pokemontcg.io returned unexpected status {response.status_code}"
                    )

                last_error = IdentificationProviderError(
                    f"pokemontcg.io returned status {response.status_code}"
                )
                logger.warning(
                    "pokemontcg.io returned status %s (attempt %d/%d), will retry",
                    response.status_code,
                    attempt,
                    MAX_ATTEMPTS,
                )

            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * attempt)

        logger.error("pokemontcg.io failed after %d attempts: %s", MAX_ATTEMPTS, last_error)
        raise IdentificationProviderError(
            "Could not reach pokemontcg.io after multiple attempts"
        ) from last_error

    @staticmethod
    def _build_query(query: IdentificationQuery, name: str) -> str:
        number = _normalize_number(query.collector_number)
        parts = [f'name:"{name}"', f"number:{number}"]
        if query.set_name:
            parts.append(f'set.name:"{query.set_name}"')
        return " ".join(parts)

    @staticmethod
    def _spacing_variants(name: str) -> list[str]:
        """pokemontcg.io is inconsistent about how a special-rarity suffix is
        joined to the Pokemon's name: "Charizard-GX" uses a hyphen, but
        "Charizard VMAX" uses a space (probably also true for VSTAR/BREAK).
        Whichever way the caller typed it, try the other one too before
        giving up -- tried in the order most likely to help, without
        repeating the original or duplicate variants."""
        variants = []
        if "-" in name:
            variants.append(name.replace("-", " "))
        if " " in name:
            variants.append(name.replace(" ", "-"))
        return [v for v in dict.fromkeys(variants) if v != name]

    @staticmethod
    def _to_candidate(item: dict) -> IdentificationCandidate:
        set_info = item.get("set") or {}
        images = item.get("images") or {}
        return IdentificationCandidate(
            external_id=item["id"],
            name=item.get("name", ""),
            collector_number=item.get("number", ""),
            set_name=set_info.get("name"),
            rarity=item.get("rarity"),
            image_url=images.get("large") or images.get("small"),
            language=None,
            source="pokemontcg.io",
        )
