from typing import Literal

from pydantic import BaseModel, Field

from app.providers.identification.base import IdentificationCandidate


class IdentifyRequest(BaseModel):
    name: str = Field(min_length=1)
    collector_number: str = Field(min_length=1)
    set_name: str | None = None
    language: str | None = None
    page: int = Field(default=1, ge=1)


class IdentifyOverride(BaseModel):
    """Optional overrides for re-identifying an existing card.

    Any field left unset falls back to the card's currently stored value.
    """

    name: str | None = Field(default=None, min_length=1)
    collector_number: str | None = Field(default=None, min_length=1)
    set_name: str | None = None
    language: str | None = None
    page: int = Field(default=1, ge=1)


IdentifyStatus = Literal["not_found", "single_match", "multiple_matches"]


class IdentifyResponse(BaseModel):
    status: IdentifyStatus
    candidates: list[IdentificationCandidate]
    # True if calling again with page+1 (same name/number/language) would
    # likely surface more candidates. Only ever True for a source that
    # paginates without an exact server-side filter -- see
    # PokemonCardComProvider. Always False for the rest, since their result
    # sets are already precise.
    has_more: bool = False
