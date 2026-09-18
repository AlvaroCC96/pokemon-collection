import asyncio

import pytest

from app.providers.identification.base import (
    IdentificationCandidate,
    IdentificationProviderError,
)
from app.providers.identification.fake import FakeIdentificationProvider
from app.schemas.identification import IdentifyRequest
from app.services import identification_service as svc
from app.services.identification_service import IdentificationProviderRegistry


def _candidate(source: str) -> IdentificationCandidate:
    return IdentificationCandidate(external_id=source, name="Charizard", collector_number="4", source=source)


def _registry(
    western=None, japanese=None, traditional_chinese=None, simplified_chinese=None
) -> IdentificationProviderRegistry:
    return IdentificationProviderRegistry(
        western=western or FakeIdentificationProvider(),
        japanese=japanese or FakeIdentificationProvider(),
        traditional_chinese=traditional_chinese or FakeIdentificationProvider(),
        simplified_chinese=simplified_chinese or FakeIdentificationProvider(),
    )


def _identify(query: IdentifyRequest, registry: IdentificationProviderRegistry):
    return asyncio.run(svc.identify(query, registry))


# --- routing ---------------------------------------------------------------


def test_language_none_routes_to_western() -> None:
    western = FakeIdentificationProvider(candidates=[_candidate("western")])
    registry = _registry(western=western)
    result = _identify(IdentifyRequest(name="Charizard ex", collector_number="4"), registry)
    assert result.candidates[0].source == "western"


@pytest.mark.parametrize("language", ["Español", "Inglés", "Ingles", "EN", "ES", "unknown-garbage"])
def test_es_en_and_unrecognized_language_route_to_western(language: str) -> None:
    western = FakeIdentificationProvider(candidates=[_candidate("western")])
    registry = _registry(western=western)
    result = _identify(
        IdentifyRequest(name="Charizard ex", collector_number="4", language=language), registry
    )
    assert result.candidates[0].source == "western"
    assert len(western.received_queries) == 1


def test_ja_routes_to_japanese_provider() -> None:
    japanese = FakeIdentificationProvider(candidates=[_candidate("japanese")])
    western = FakeIdentificationProvider(candidates=[_candidate("western")])
    registry = _registry(western=western, japanese=japanese)
    result = _identify(
        IdentifyRequest(name="Charizard", collector_number="4", language="Japonés"), registry
    )
    assert result.candidates[0].source == "japanese"
    assert western.received_queries == []


def test_zh_tw_routes_to_traditional_chinese_provider() -> None:
    tw = FakeIdentificationProvider(candidates=[_candidate("tw")])
    cn = FakeIdentificationProvider(candidates=[_candidate("cn")])
    registry = _registry(traditional_chinese=tw, simplified_chinese=cn)
    result = _identify(
        IdentifyRequest(name="Charizard", collector_number="4", language="ZH-TW"), registry
    )
    assert result.candidates[0].source == "tw"
    assert cn.received_queries == []


def test_zh_cn_routes_to_simplified_chinese_provider() -> None:
    tw = FakeIdentificationProvider(candidates=[_candidate("tw")])
    cn = FakeIdentificationProvider(candidates=[_candidate("cn")])
    registry = _registry(traditional_chinese=tw, simplified_chinese=cn)
    result = _identify(
        IdentifyRequest(name="Charizard", collector_number="4", language="ZH-CN"), registry
    )
    assert result.candidates[0].source == "cn"
    assert tw.received_queries == []


def test_generic_chinese_tries_traditional_then_simplified() -> None:
    tw = FakeIdentificationProvider(candidates=[])  # finds nothing
    cn = FakeIdentificationProvider(candidates=[_candidate("cn")])
    registry = _registry(traditional_chinese=tw, simplified_chinese=cn)
    result = _identify(
        IdentifyRequest(name="Charizard", collector_number="4", language="Chino"), registry
    )
    assert result.status == "single_match"
    assert result.candidates[0].source == "cn"
    assert len(tw.received_queries) == 1  # tried first
    assert len(cn.received_queries) == 1  # then this


def test_generic_chinese_not_found_when_neither_variant_has_it() -> None:
    registry = _registry(
        traditional_chinese=FakeIdentificationProvider(candidates=[]),
        simplified_chinese=FakeIdentificationProvider(candidates=[]),
    )
    result = _identify(
        IdentifyRequest(name="Nonexistent", collector_number="4", language="Chino"), registry
    )
    assert result.status == "not_found"


# --- status mapping (0/1/N), unaffected by which provider answered --------


def test_not_found_status() -> None:
    registry = _registry(western=FakeIdentificationProvider(candidates=[]))
    result = _identify(IdentifyRequest(name="Nope", collector_number="1"), registry)
    assert result.status == "not_found"
    assert result.candidates == []


def test_single_match_status() -> None:
    registry = _registry(western=FakeIdentificationProvider(candidates=[_candidate("a")]))
    result = _identify(IdentifyRequest(name="Charizard", collector_number="4"), registry)
    assert result.status == "single_match"


def test_multiple_matches_status() -> None:
    registry = _registry(
        western=FakeIdentificationProvider(candidates=[_candidate("a"), _candidate("b")])
    )
    result = _identify(IdentifyRequest(name="Charizard", collector_number="4"), registry)
    assert result.status == "multiple_matches"


# --- optional fields / unicode / provider failures -------------------------


def test_candidate_with_all_optional_fields_absent() -> None:
    minimal = IdentificationCandidate(external_id="x", name="リザードン")
    registry = _registry(western=FakeIdentificationProvider(candidates=[minimal]))
    result = _identify(IdentifyRequest(name="Charizard", collector_number="4"), registry)
    c = result.candidates[0]
    assert c.collector_number is None
    assert c.set_name is None
    assert c.rarity is None
    assert c.image_url is None


def test_japanese_unicode_name_round_trips_untouched() -> None:
    candidate = IdentificationCandidate(external_id="x", name="リザードンGX", collector_number="20")
    japanese = FakeIdentificationProvider(candidates=[candidate])
    registry = _registry(japanese=japanese)
    result = _identify(
        IdentifyRequest(name="Charizard GX", collector_number="20", language="JA"), registry
    )
    # the catalog's original-script name is preserved, never translated back
    assert result.candidates[0].name == "リザードンGX"


def test_chinese_unicode_name_round_trips_untouched() -> None:
    candidate = IdentificationCandidate(external_id="x", name="噴火龍 GX", collector_number="4")
    tw = FakeIdentificationProvider(candidates=[candidate])
    registry = _registry(traditional_chinese=tw)
    result = _identify(
        IdentifyRequest(name="Charizard GX", collector_number="4", language="ZH-TW"), registry
    )
    assert result.candidates[0].name == "噴火龍 GX"


def test_collector_number_is_forwarded_to_the_selected_provider() -> None:
    japanese = FakeIdentificationProvider(candidates=[])
    registry = _registry(japanese=japanese)
    _identify(IdentifyRequest(name="Charizard", collector_number="004/151", language="JA"), registry)
    assert japanese.received_queries[0].collector_number == "004/151"


class RaisingProvider:
    name = "raising"

    async def find_candidates(self, query):
        raise IdentificationProviderError("external provider is down")


def test_provider_failure_propagates_as_identification_provider_error_not_a_crash() -> None:
    registry = _registry(western=RaisingProvider())
    with pytest.raises(IdentificationProviderError):
        _identify(IdentifyRequest(name="Charizard", collector_number="4"), registry)


def test_japanese_provider_failure_does_not_crash_when_it_is_a_fallback_chain() -> None:
    # Mirrors how `japanese` is really built: a Composite of [official, tcgdex].
    # If the first raises, the second should still get a chance.
    from app.providers.identification.composite import CompositeIdentificationProvider

    fallback = FakeIdentificationProvider(candidates=[_candidate("fallback")])
    composite = CompositeIdentificationProvider([RaisingProvider(), fallback])
    registry = _registry(japanese=composite)

    result = _identify(
        IdentifyRequest(name="Charizard", collector_number="4", language="JA"), registry
    )
    assert result.candidates[0].source == "fallback"


# --- pagination ("cargar más") ----------------------------------------------


def test_has_more_forwarded_from_provider_to_response() -> None:
    japanese = FakeIdentificationProvider(candidates=[_candidate("a"), _candidate("b")], has_more=True)
    registry = _registry(japanese=japanese)
    result = _identify(
        IdentifyRequest(name="Pikachu", collector_number="1", language="JA"), registry
    )
    assert result.has_more is True


def test_has_more_defaults_false_for_providers_that_dont_paginate() -> None:
    registry = _registry(western=FakeIdentificationProvider(candidates=[_candidate("a")]))
    result = _identify(IdentifyRequest(name="Charizard", collector_number="4"), registry)
    assert result.has_more is False


def test_page_number_is_forwarded_to_the_selected_provider() -> None:
    japanese = FakeIdentificationProvider(candidates=[])
    registry = _registry(japanese=japanese)
    _identify(
        IdentifyRequest(name="Pikachu", collector_number="1", language="JA", page=3), registry
    )
    assert japanese.received_queries[0].page == 3


def test_page_defaults_to_one() -> None:
    western = FakeIdentificationProvider(candidates=[])
    registry = _registry(western=western)
    _identify(IdentifyRequest(name="Charizard", collector_number="4"), registry)
    assert western.received_queries[0].page == 1
