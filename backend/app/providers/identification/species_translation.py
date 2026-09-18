import logging
import re

import httpx

logger = logging.getLogger(__name__)

POKEAPI_BASE_URL = "https://pokeapi.co/api/v2"
REQUEST_TIMEOUT_SECONDS = 10.0

# TCG rarity/mechanic suffixes -- stripped so we're left with just the
# species name to translate (e.g. "Charizard GX" -> "Charizard"). Official
# regional catalogs (pokemon-card.com, TCGdex ja/zh-tw/zh-cn) store card
# names in the LOCAL SCRIPT, so a name typed in Spanish/English never
# matches directly; PokeAPI (free, no key, ~14 languages of official
# Pokemon species names) bridges that gap.
_SUFFIX_MARKERS = {"ex", "gx", "v", "vmax", "vstar", "break"}


def strip_suffix_markers(name: str) -> str:
    words = re.split(r"[\s-]+", name.strip())
    while words and words[-1].lower() in _SUFFIX_MARKERS:
        words.pop()
    return " ".join(words)


async def translate_species_name(name: str, pokeapi_lang: str) -> str | None:
    """Best-effort: returns None (never raises) if PokeAPI is unreachable or
    doesn't know the species -- callers fall back to the stripped original
    name, which will typically just find nothing in a non-Latin catalog."""
    species_slug = strip_suffix_markers(name).strip().lower().replace(" ", "-")
    if not species_slug:
        return None

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{POKEAPI_BASE_URL}/pokemon-species/{species_slug}")
    except httpx.RequestError as exc:
        logger.warning("PokeAPI request failed for %r: %s", species_slug, exc)
        return None

    if response.status_code != 200:
        logger.info("PokeAPI has no species %r (status %s)", species_slug, response.status_code)
        return None

    for entry in response.json().get("names", []):
        if entry["language"]["name"] == pokeapi_lang:
            return entry["name"]
    return None
