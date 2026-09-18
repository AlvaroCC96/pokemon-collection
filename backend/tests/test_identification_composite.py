import asyncio

import pytest

from app.providers.identification.base import IdentificationCandidate, IdentificationQuery
from app.providers.identification.composite import CompositeIdentificationProvider
from app.providers.identification.fake import FakeIdentificationProvider


def _candidate(external_id: str = "x") -> IdentificationCandidate:
    return IdentificationCandidate(external_id=external_id, name="Charizard", collector_number="4")


class RaisingProvider:
    name = "raising"

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def find_candidates(self, query: IdentificationQuery):
        raise self._exc


def _query() -> IdentificationQuery:
    return IdentificationQuery(name="Charizard", collector_number="4")


def test_returns_primary_result_without_trying_fallback() -> None:
    primary = FakeIdentificationProvider(candidates=[_candidate("primary")])
    fallback = FakeIdentificationProvider(candidates=[_candidate("fallback")])
    composite = CompositeIdentificationProvider([primary, fallback])

    result = asyncio.run(composite.find_candidates(_query()))

    assert [c.external_id for c in result.candidates] == ["primary"]
    assert fallback.received_queries == []  # never called


def test_falls_back_when_primary_finds_nothing() -> None:
    primary = FakeIdentificationProvider(candidates=[])
    fallback = FakeIdentificationProvider(candidates=[_candidate("fallback")])
    composite = CompositeIdentificationProvider([primary, fallback])

    result = asyncio.run(composite.find_candidates(_query()))

    assert [c.external_id for c in result.candidates] == ["fallback"]
    assert len(fallback.received_queries) == 1


def test_returns_empty_when_all_providers_find_nothing() -> None:
    composite = CompositeIdentificationProvider(
        [FakeIdentificationProvider(candidates=[]), FakeIdentificationProvider(candidates=[])]
    )
    result = asyncio.run(composite.find_candidates(_query()))
    assert result.candidates == []
    assert result.has_more is False


def test_forwards_has_more_from_the_winning_provider() -> None:
    primary = FakeIdentificationProvider(candidates=[_candidate("a")], has_more=True)
    composite = CompositeIdentificationProvider([primary])
    result = asyncio.run(composite.find_candidates(_query()))
    assert result.has_more is True


def test_skips_provider_that_errors_and_uses_next() -> None:
    from app.providers.identification.base import IdentificationProviderError

    primary = RaisingProvider(IdentificationProviderError("boom"))
    fallback = FakeIdentificationProvider(candidates=[_candidate("fallback")])
    composite = CompositeIdentificationProvider([primary, fallback])

    result = asyncio.run(composite.find_candidates(_query()))
    assert [c.external_id for c in result.candidates] == ["fallback"]


def test_raises_when_every_provider_errors() -> None:
    from app.providers.identification.base import IdentificationProviderError

    composite = CompositeIdentificationProvider(
        [
            RaisingProvider(IdentificationProviderError("first failure")),
            RaisingProvider(IdentificationProviderError("second failure")),
        ]
    )
    with pytest.raises(IdentificationProviderError, match="second failure"):
        asyncio.run(composite.find_candidates(_query()))
