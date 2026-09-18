import logging

import httpx

from app.providers.identification.base import IdentificationCandidate, IdentificationQuery, IdentificationResult
from app.providers.identification.species_translation import strip_suffix_markers, translate_species_name

logger = logging.getLogger(__name__)

BASE_URL = "https://api.tcgdex.net/v2"
REQUEST_TIMEOUT_SECONDS = 10.0
MAX_CANDIDATES = 10


def _strip_leading_zeros(number: str) -> str:
    return number.lstrip("0") or "0"


class TCGdexLanguageProvider:
    """IdentificationProvider for ONE TCGdex language catalog (free, no API
    key). Used as `TraditionalChineseIdentificationProvider` (zh-tw/zh-hant)
    and `SimplifiedChineseIdentificationProvider` (zh-cn/zh-hans) -- same
    mechanics, different catalog, so implemented once and parameterized
    rather than duplicated. Also used as the Japanese fallback behind the
    official pokemon-card.com search (see pokemon_card_com.py).

    Non-English TCGdex catalogs store card names in the LOCAL SCRIPT, so the
    species name is translated via PokeAPI before searching (see
    species_translation.py and ARCHITECTURE.md).

    Best-effort by design: any failure (PokeAPI down, TCGdex down, species
    not found) returns an empty list rather than raising.
    """

    def __init__(self, tcgdex_lang: str, pokeapi_lang: str, name: str) -> None:
        self._tcgdex_lang = tcgdex_lang
        self._pokeapi_lang = pokeapi_lang
        self.name = name

    async def find_candidates(self, query: IdentificationQuery) -> IdentificationResult:
        translated = await translate_species_name(query.name, self._pokeapi_lang)
        search_name = translated or strip_suffix_markers(query.name)
        if not search_name:
            return IdentificationResult(candidates=[])

        number = _strip_leading_zeros(query.collector_number.split("/")[0].strip())

        logger.info(
            "Searching TCGdex lang=%s for translated name=%r (original=%r) number=%r",
            self._tcgdex_lang,
            search_name,
            query.name,
            number,
        )
        listing = await self._search_by_name(search_name)
        matches = [
            item for item in listing if _strip_leading_zeros(str(item.get("localId", ""))) == number
        ]
        if not matches:
            return IdentificationResult(candidates=[])

        candidates = []
        for item in matches[:MAX_CANDIDATES]:
            detail = await self._fetch_card_detail(item["id"])
            if detail:
                candidates.append(self._to_candidate(detail))
        logger.info("TCGdex (%s) found %d candidate(s)", self._tcgdex_lang, len(candidates))
        # already filtered by number, so a single page is always exact
        return IdentificationResult(candidates=candidates, has_more=False)

    async def _search_by_name(self, name: str) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    f"{BASE_URL}/{self._tcgdex_lang}/cards", params={"name": name}
                )
        except httpx.RequestError as exc:
            logger.warning(
                "TCGdex search failed (lang=%s, name=%r): %s", self._tcgdex_lang, name, exc
            )
            return []

        if response.status_code != 200:
            logger.warning(
                "TCGdex returned status %s (lang=%s, name=%r)",
                response.status_code,
                self._tcgdex_lang,
                name,
            )
            return []

        return response.json()

    async def _fetch_card_detail(self, card_id: str) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.get(f"{BASE_URL}/{self._tcgdex_lang}/cards/{card_id}")
        except httpx.RequestError as exc:
            logger.warning("TCGdex card detail failed (id=%s): %s", card_id, exc)
            return None

        if response.status_code != 200:
            return None
        return response.json()

    def _to_candidate(self, item: dict) -> IdentificationCandidate:
        set_info = item.get("set") or {}
        image_base = item.get("image")
        return IdentificationCandidate(
            external_id=item["id"],
            name=item.get("name", ""),
            collector_number=item.get("localId"),
            set_name=set_info.get("name"),
            rarity=item.get("rarity"),
            image_url=f"{image_base}/high.webp" if image_base else None,
            language=None,
            source=f"tcgdex:{self._tcgdex_lang}",
        )
