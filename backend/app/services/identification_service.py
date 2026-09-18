import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.language_codes import normalize_language_code
from app.providers.identification.base import (
    IdentificationCandidate,
    IdentificationProvider,
    IdentificationQuery,
)
from app.providers.identification.composite import CompositeIdentificationProvider
from app.providers.identification.pokemon_card_com import PokemonCardComProvider
from app.providers.identification.pokemon_tcg_io import PokemonTCGIOProvider
from app.providers.identification.tcgdex import TCGdexLanguageProvider
from app.schemas.identification import IdentifyOverride, IdentifyRequest, IdentifyResponse
from app.services.card_service import get_card

logger = logging.getLogger(__name__)


@dataclass
class IdentificationProviderRegistry:
    """One provider (or provider chain) per region. `identify()` does the
    routing based on the query's language -- no region-specific logic lives
    in routes/controllers (ETAPA 5.5, see ARCHITECTURE.md)."""

    western: IdentificationProvider  # ES / EN / language=null -- original pokemontcg.io behavior
    japanese: IdentificationProvider  # JA
    traditional_chinese: IdentificationProvider  # ZH-TW
    simplified_chinese: IdentificationProvider  # ZH-CN


def get_identification_providers() -> IdentificationProviderRegistry:
    """FastAPI dependency. Overridden in tests to avoid real network calls."""
    settings = get_settings()
    pokemon_tcg_io = PokemonTCGIOProvider(api_key=settings.pokemon_tcg_io_api_key)
    tcgdex_ja = TCGdexLanguageProvider("ja", "ja", name="tcgdex_ja")
    tcgdex_zh_tw = TCGdexLanguageProvider("zh-tw", "zh-hant", name="tcgdex_zh_tw")
    tcgdex_zh_cn = TCGdexLanguageProvider("zh-cn", "zh-hans", name="tcgdex_zh_cn")

    return IdentificationProviderRegistry(
        western=pokemon_tcg_io,
        # Official pokemon-card.com search first (real name+image search,
        # no collector number available); TCGdex ja as fallback. See
        # pokemon_card_com.py for why the official site alone isn't enough.
        japanese=CompositeIdentificationProvider([PokemonCardComProvider(), tcgdex_ja]),
        traditional_chinese=tcgdex_zh_tw,
        simplified_chinese=tcgdex_zh_cn,
    )


def _select_provider(
    language: str | None, registry: IdentificationProviderRegistry
) -> IdentificationProvider:
    """The ONLY place region-specific routing is decided. `language=None`
    or an unrecognized value preserves the original ES/EN behavior
    unchanged -- this never fans out to every regional catalog on a plain
    search. A generic "Chinese" (code ZH, variant unspecified) tries
    Traditional then Simplified in that documented order rather than
    guessing a region silently (ETAPA 5.5 section 5)."""
    code = normalize_language_code(language)
    if code == "JA":
        return registry.japanese
    if code == "ZH-TW":
        return registry.traditional_chinese
    if code == "ZH-CN":
        return registry.simplified_chinese
    if code == "ZH":
        return CompositeIdentificationProvider(
            [registry.traditional_chinese, registry.simplified_chinese]
        )
    return registry.western


def _status_for(candidates: list[IdentificationCandidate]) -> str:
    if not candidates:
        return "not_found"
    if len(candidates) == 1:
        return "single_match"
    return "multiple_matches"


async def identify(
    query: IdentifyRequest, registry: IdentificationProviderRegistry
) -> IdentifyResponse:
    logger.info(
        "Identifying card name=%r number=%r language=%r page=%d",
        query.name,
        query.collector_number,
        query.language,
        query.page,
    )
    provider = _select_provider(query.language, registry)
    result = await provider.find_candidates(IdentificationQuery(**query.model_dump()))
    status = _status_for(result.candidates)
    logger.info(
        "Identification result: status=%s candidates=%d has_more=%s (provider=%s)",
        status,
        len(result.candidates),
        result.has_more,
        provider.name,
    )
    return IdentifyResponse(status=status, candidates=result.candidates, has_more=result.has_more)


async def identify_existing_card(
    db: Session,
    card_id: int,
    override: IdentifyOverride | None,
    registry: IdentificationProviderRegistry,
) -> IdentifyResponse:
    card = get_card(db, card_id)  # raises CardNotFoundError -> handled as 404 in main.py

    override_data = override.model_dump(exclude_unset=True) if override else {}
    query = IdentifyRequest(
        name=override_data.get("name", card.name),
        collector_number=override_data.get("collector_number", card.collector_number),
        set_name=override_data.get("set_name", card.set_name),
        language=override_data.get("language", card.language),
        page=override_data.get("page", 1),
    )
    return await identify(query, registry)
