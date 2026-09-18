import asyncio

import pytest

from app.providers.identification import pokemon_card_com as module
from app.providers.identification.base import IdentificationQuery
from app.providers.identification.pokemon_card_com import PokemonCardComProvider


class FakeResponse:
    def __init__(self, status_code: int, payload=None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, responses_by_url_fragment: dict[str, list[FakeResponse]]) -> None:
        self._responses = {k: list(v) for k, v in responses_by_url_fragment.items()}
        self.requested = []

    def __call__(self, *args, **kwargs) -> "FakeAsyncClient":
        return self

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args) -> None:
        return None

    async def get(self, url: str, params: dict | None = None, **kwargs) -> FakeResponse:
        self.requested.append((url, params))
        matching = [f for f in self._responses if f in url]
        if not matching:
            raise AssertionError(f"Unexpected URL requested: {url}")
        fragment = max(matching, key=len)
        responses = self._responses[fragment]
        if not responses:
            raise AssertionError(f"No more fake responses for {fragment!r}")
        return responses.pop(0)


def _install(monkeypatch: pytest.MonkeyPatch, responses: dict[str, list[FakeResponse]]) -> FakeAsyncClient:
    client = FakeAsyncClient(responses)
    monkeypatch.setattr(module.httpx, "AsyncClient", client)
    return client


def test_translates_before_searching_and_maps_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install(
        monkeypatch,
        {
            "pokeapi.co": [
                FakeResponse(200, {"names": [{"language": {"name": "ja"}, "name": "リザードン"}]})
            ],
            "resultAPI.php": [
                FakeResponse(
                    200,
                    {
                        "result": 1,
                        "errMsg": "",
                        "cardList": [
                            {
                                "cardID": "50714",
                                "cardThumbFile": "/assets/images/card_images/large/M6a/050714_P_RIZADON.jpg",
                                "cardNameAltText": "リザードン",
                                "cardNameViewText": "リザードン",
                            }
                        ],
                    },
                )
            ],
        },
    )

    provider = PokemonCardComProvider()
    query = IdentificationQuery(name="Charizard", collector_number="137/103", language="Japonés")
    result = asyncio.run(provider.find_candidates(query))

    assert len(result.candidates) == 1
    c = result.candidates[0]
    assert c.external_id == "50714"
    assert c.name == "リザードン"
    assert c.image_url == "https://www.pokemon-card.com/assets/images/card_images/large/M6a/050714_P_RIZADON.jpg"
    assert c.source == "pokemon-card.com"
    # honest about what this source can't provide -- never guessed
    assert c.collector_number is None
    assert c.set_name is None
    assert c.rarity is None
    assert result.has_more is False  # thisPage/maxPage absent -> defaults to no more pages

    # confirms the JAPANESE (translated) name was searched, not the English one
    search_call = next(p for u, p in client.requested if "resultAPI.php" in u)
    assert search_call["keyword"] == "リザードン"
    assert search_call["page"] == 1  # default


def test_forwards_page_param_and_reports_has_more(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install(
        monkeypatch,
        {
            "pokeapi.co": [FakeResponse(200, {"names": [{"language": {"name": "ja"}, "name": "ピカチュウ"}]})],
            "resultAPI.php": [
                FakeResponse(
                    200,
                    {
                        "result": 1,
                        "hitCnt": 327,
                        "thisPage": 2,
                        "maxPage": 9,
                        "cardList": [
                            {"cardID": "1", "cardNameViewText": "ピカチュウ", "cardThumbFile": "/x/1.jpg"}
                        ],
                    },
                )
            ],
        },
    )
    provider = PokemonCardComProvider()
    query = IdentificationQuery(name="Pikachu", collector_number="1", language="Japonés", page=2)
    result = asyncio.run(provider.find_candidates(query))

    assert result.has_more is True
    search_call = next(p for u, p in client.requested if "resultAPI.php" in u)
    assert search_call["page"] == 2


def test_has_more_false_on_last_page(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {
            "pokeapi.co": [FakeResponse(200, {"names": [{"language": {"name": "ja"}, "name": "ピカチュウ"}]})],
            "resultAPI.php": [
                FakeResponse(
                    200,
                    {
                        "result": 1,
                        "hitCnt": 327,
                        "thisPage": 9,
                        "maxPage": 9,
                        "cardList": [
                            {"cardID": "1", "cardNameViewText": "ピカチュウ", "cardThumbFile": "/x/1.jpg"}
                        ],
                    },
                )
            ],
        },
    )
    provider = PokemonCardComProvider()
    query = IdentificationQuery(name="Pikachu", collector_number="1", language="Japonés", page=9)
    result = asyncio.run(provider.find_candidates(query))
    assert result.has_more is False


def test_returns_empty_when_search_api_reports_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {
            "pokeapi.co": [FakeResponse(200, {"names": [{"language": {"name": "ja"}, "name": "リザードン"}]})],
            "resultAPI.php": [FakeResponse(200, {"result": 0, "errMsg": "some error", "cardList": []})],
        },
    )
    provider = PokemonCardComProvider()
    query = IdentificationQuery(name="Charizard", collector_number="1", language="Japonés")
    result = asyncio.run(provider.find_candidates(query))
    assert result.candidates == []


def test_returns_empty_on_network_failure_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    class FailingClient:
        def __call__(self, *a, **k):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def get(self, *a, **k):
            raise httpx.ConnectError("boom")

    monkeypatch.setattr(module.httpx, "AsyncClient", FailingClient())

    async def fake_translate(name: str, lang: str) -> str:
        return "リザードン"

    monkeypatch.setattr(module, "translate_species_name", fake_translate)

    provider = PokemonCardComProvider()
    query = IdentificationQuery(name="Charizard", collector_number="1", language="Japonés")
    result = asyncio.run(provider.find_candidates(query))
    assert result.candidates == []


def test_returns_empty_when_name_has_no_translatable_species(monkeypatch: pytest.MonkeyPatch) -> None:
    # "ex" alone strips down to an empty species name -- nothing to search
    # for, and no HTTP call should even be attempted.
    provider = PokemonCardComProvider()
    query = IdentificationQuery(name="ex", collector_number="1", language="Japonés")
    result = asyncio.run(provider.find_candidates(query))
    assert result.candidates == []
