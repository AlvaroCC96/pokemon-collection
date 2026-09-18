import asyncio

import pytest

from app.providers.identification import tcgdex as tcgdex_module
from app.providers.identification.base import IdentificationQuery
from app.providers.identification.tcgdex import TCGdexLanguageProvider, _strip_leading_zeros


def test_strip_leading_zeros() -> None:
    assert _strip_leading_zeros("074") == "74"
    assert _strip_leading_zeros("4") == "4"
    assert _strip_leading_zeros("00") == "0"


class FakeResponse:
    def __init__(self, status_code: int, payload=None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeAsyncClient:
    """Returns canned responses keyed by URL substring (most specific/longest
    match wins, so a card detail URL isn't mistaken for the search listing
    endpoint that's also a substring of it)."""

    def __init__(self, responses_by_url_fragment: dict[str, list[FakeResponse]]) -> None:
        self._responses = {k: list(v) for k, v in responses_by_url_fragment.items()}
        self.requested_urls: list[str] = []

    def __call__(self, *args, **kwargs) -> "FakeAsyncClient":
        return self

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args) -> None:
        return None

    async def get(self, url: str, params: dict | None = None, **kwargs) -> FakeResponse:
        full = url + ("?" + "&".join(f"{k}={v}" for k, v in (params or {}).items()) if params else "")
        self.requested_urls.append(full)
        matching = [f for f in self._responses if f in url]
        if not matching:
            raise AssertionError(f"Unexpected URL requested: {full}")
        fragment = max(matching, key=len)
        responses = self._responses[fragment]
        if not responses:
            raise AssertionError(f"No more fake responses for fragment {fragment!r} (url={full})")
        return responses.pop(0)


def _install(monkeypatch: pytest.MonkeyPatch, responses: dict[str, list[FakeResponse]]) -> FakeAsyncClient:
    client = FakeAsyncClient(responses)
    monkeypatch.setattr(tcgdex_module.httpx, "AsyncClient", client)
    return client


def _zh_tw_provider() -> TCGdexLanguageProvider:
    return TCGdexLanguageProvider("zh-tw", "zh-hant", name="tcgdex_zh_tw")


def _zh_cn_provider() -> TCGdexLanguageProvider:
    return TCGdexLanguageProvider("zh-cn", "zh-hans", name="tcgdex_zh_cn")


def _ja_provider() -> TCGdexLanguageProvider:
    return TCGdexLanguageProvider("ja", "ja", name="tcgdex_ja")


def test_find_candidates_translates_and_matches_chinese_card(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install(
        monkeypatch,
        {
            "pokeapi.co": [
                FakeResponse(200, {"names": [{"language": {"name": "zh-hant"}, "name": "噴火龍"}]})
            ],
            "zh-tw/cards/CSM1aC-4": [
                FakeResponse(
                    200,
                    {
                        "id": "CSM1aC-4",
                        "localId": "4",
                        "name": "噴火龍 GX",
                        "rarity": "RR",
                        "set": {"id": "CSM1aC", "name": "橫空出世"},
                        "image": "https://assets.tcgdex.net/zh-tw/SM/CSM1aC/4",
                    },
                )
            ],
            "zh-tw/cards": [FakeResponse(200, [{"id": "CSM1aC-4", "localId": "4", "name": "噴火龍 GX"}])],
        },
    )

    provider = _zh_tw_provider()
    query = IdentificationQuery(name="Charizard GX", collector_number="004/151", language="Chino")
    candidates = asyncio.run(provider.find_candidates(query)).candidates

    assert len(candidates) == 1
    assert candidates[0].external_id == "CSM1aC-4"
    assert candidates[0].set_name == "橫空出世"
    assert candidates[0].image_url == "https://assets.tcgdex.net/zh-tw/SM/CSM1aC/4/high.webp"
    assert candidates[0].source == "tcgdex:zh-tw"
    assert any("噴火龍" in u for u in client.requested_urls)


def test_find_candidates_missing_image_field_is_null_not_a_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(
        monkeypatch,
        {
            "pokeapi.co": [FakeResponse(200, {"names": [{"language": {"name": "zh-hans"}, "name": "喷火龙"}]})],
            "zh-cn/cards/CSM1aC-4": [
                FakeResponse(
                    200,
                    {
                        "id": "CSM1aC-4",
                        "localId": "4",
                        "name": "喷火龙 GX",
                        "rarity": "RR",
                        "set": {"id": "CSM1aC", "name": "横空出世"},
                        "image": None,
                    },
                )
            ],
            "zh-cn/cards": [FakeResponse(200, [{"id": "CSM1aC-4", "localId": "4", "name": "喷火龙 GX"}])],
        },
    )

    provider = _zh_cn_provider()
    query = IdentificationQuery(name="Charizard GX", collector_number="4", language="Chino simplificado")
    candidates = asyncio.run(provider.find_candidates(query)).candidates

    assert len(candidates) == 1
    assert candidates[0].image_url is None
    assert candidates[0].source == "tcgdex:zh-cn"


def test_find_candidates_returns_empty_when_pokeapi_has_no_species(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, {"pokeapi.co": [FakeResponse(404)], "ja/cards": [FakeResponse(200, [])]})
    provider = _ja_provider()
    query = IdentificationQuery(name="Some Unknown Fakemon", collector_number="1", language="Japonés")
    candidates = asyncio.run(provider.find_candidates(query)).candidates
    assert candidates == []


def test_find_candidates_filters_out_wrong_number(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {
            "pokeapi.co": [FakeResponse(200, {"names": [{"language": {"name": "ja"}, "name": "リザードン"}]})],
            "ja/cards": [
                FakeResponse(
                    200,
                    [
                        {"id": "SM3-20", "localId": "20", "name": "リザードンGX"},
                        {"id": "SM9-6", "localId": "6", "name": "リザードンGX"},
                    ],
                )
            ],
            "ja/cards/SM9-6": [
                FakeResponse(
                    200,
                    {
                        "id": "SM9-6",
                        "localId": "6",
                        "name": "リザードンGX",
                        "rarity": "RR",
                        "set": {"id": "SM9", "name": "タッグボルト"},
                        "image": None,
                    },
                )
            ],
            # deliberately NO "ja/cards/SM3-20" entry: if the code mistakenly
            # fetched detail for the non-matching localId "20", the fake
            # client raises AssertionError and fails this test.
        },
    )
    provider = _ja_provider()
    query = IdentificationQuery(name="Charizard GX", collector_number="6", language="Japonés")
    candidates = asyncio.run(provider.find_candidates(query)).candidates
    assert len(candidates) == 1
    assert candidates[0].external_id == "SM9-6"


def test_find_candidates_no_matches_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {
            "pokeapi.co": [FakeResponse(200, {"names": [{"language": {"name": "zh-hant"}, "name": "皮卡丘"}]})],
            "zh-tw/cards": [FakeResponse(200, [])],
        },
    )
    provider = _zh_tw_provider()
    query = IdentificationQuery(name="Pikachu", collector_number="25", language="Chino")
    assert asyncio.run(provider.find_candidates(query)).candidates == []
