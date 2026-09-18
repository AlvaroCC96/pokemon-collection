from typing import Protocol

from pydantic import BaseModel, Field


class IdentificationQuery(BaseModel):
    name: str
    collector_number: str
    set_name: str | None = None
    language: str | None = None
    # 1-based. Most providers ignore this (their result sets are already
    # small/precise, e.g. filtered by number); a source with no number
    # filter and hundreds of same-name prints (pokemon-card.com) uses it to
    # fetch the next page instead of silently truncating results.
    page: int = Field(default=1, ge=1)


class IdentificationCandidate(BaseModel):
    external_id: str
    name: str
    # Nullable: some official regional catalogs (e.g. pokemon-card.com's
    # public search) don't expose a collector number at all. Never invent
    # one -- null means "not available from this source", not "unknown/0".
    collector_number: str | None = None
    set_name: str | None = None
    rarity: str | None = None
    image_url: str | None = None
    language: str | None = None
    source: str | None = None  # which provider/catalog produced this candidate


class IdentificationResult(BaseModel):
    candidates: list[IdentificationCandidate]
    # True if a further `page` for this same query would likely return more
    # candidates. Only ever True for a source that both paginates and can't
    # filter down to an exact match server-side (see PokemonCardComProvider);
    # every other provider's result sets are already precise, so this
    # defaults to False and providers that don't paginate never need to
    # think about it.
    has_more: bool = False


class IdentificationProviderError(Exception):
    """Raised when an identification provider cannot be reached or returns an unexpected response."""


class IdentificationProvider(Protocol):
    name: str

    async def find_candidates(self, query: IdentificationQuery) -> IdentificationResult: ...
