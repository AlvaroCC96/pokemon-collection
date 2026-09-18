import logging

import httpx

from app.providers.identification.base import IdentificationCandidate, IdentificationQuery, IdentificationResult
from app.providers.identification.species_translation import strip_suffix_markers, translate_species_name

logger = logging.getLogger(__name__)

BASE_URL = "https://www.pokemon-card.com/card-search/resultAPI.php"
SITE_ORIGIN = "https://www.pokemon-card.com"
REQUEST_TIMEOUT_SECONDS = 10.0


class PokemonCardComProvider:
    """IdentificationProvider backed by the OFFICIAL Japanese Pokemon TCG
    site's internal search endpoint.

    This is a real, undocumented-but-functional JSON API: `resultAPI.php`
    is the exact endpoint the site's own search page calls (confirmed by
    reading its production JavaScript, not guessed) -- including its `page`
    parameter, used the same way here (`PTC.paginationRequest`). It is NOT
    a scraper -- no HTML is parsed, only a JSON response the site serves.

    Known, load-bearing limitation: the response gives name + thumbnail
    image only -- no collector number, set, or rarity. Getting those would
    require scraping each result's detail page (unstable HTML, not a
    contracted API), which was deliberately not built -- see
    ARCHITECTURE.md. Candidates carry `collector_number`/`set_name`/
    `rarity` as null rather than guessed; the user disambiguates visually
    by image when a name matches multiple prints.

    The site's search only matches Japanese-script names, so the species
    name is translated via PokeAPI first (see species_translation.py).

    Pagination: a common name (Pikachu, Charizard...) can have hundreds of
    prints, and this source still has no number filter -- fetching more
    pages doesn't let US narrow down to an exact match, but it DOES let a
    human keep browsing by image until they recognize their card, which a
    number filter couldn't do here anyway. `query.page` is forwarded as-is;
    `has_more` reflects the site's own `thisPage < maxPage`.
    """

    name = "pokemon_card_com"

    async def find_candidates(self, query: IdentificationQuery) -> IdentificationResult:
        translated = await translate_species_name(query.name, "ja")
        search_name = translated or strip_suffix_markers(query.name)
        if not search_name:
            return IdentificationResult(candidates=[])

        logger.info(
            "Searching pokemon-card.com for translated name=%r (original=%r) page=%d",
            search_name,
            query.name,
            query.page,
        )

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    BASE_URL,
                    params={
                        "keyword": search_name,
                        "sm_and_keyword": "true",
                        "regulation": "all",
                        "page": query.page,
                    },
                )
        except httpx.RequestError as exc:
            logger.warning("pokemon-card.com request failed: %s", exc)
            return IdentificationResult(candidates=[])

        if response.status_code != 200:
            logger.warning("pokemon-card.com returned status %s", response.status_code)
            return IdentificationResult(candidates=[])

        payload = response.json()
        if payload.get("result") != 1:
            logger.info("pokemon-card.com search error: %s", payload.get("errMsg"))
            return IdentificationResult(candidates=[])

        candidates = [self._to_candidate(item) for item in payload.get("cardList", [])]
        this_page = payload.get("thisPage", query.page)
        max_page = payload.get("maxPage", this_page)
        has_more = this_page < max_page
        logger.info(
            "pokemon-card.com found %d candidate(s) (page %s/%s, hitCnt=%s)",
            len(candidates),
            this_page,
            max_page,
            payload.get("hitCnt"),
        )
        return IdentificationResult(candidates=candidates, has_more=has_more)

    @staticmethod
    def _to_candidate(item: dict) -> IdentificationCandidate:
        thumb = item.get("cardThumbFile")
        return IdentificationCandidate(
            external_id=str(item.get("cardID", "")),
            name=item.get("cardNameViewText") or item.get("cardNameAltText") or "",
            collector_number=None,
            set_name=None,
            rarity=None,
            image_url=f"{SITE_ORIGIN}{thumb}" if thumb else None,
            language=None,
            source="pokemon-card.com",
        )
