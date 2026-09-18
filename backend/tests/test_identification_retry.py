import asyncio

import pytest

from app.providers.identification import pokemon_tcg_io as provider_module
from app.providers.identification.base import IdentificationProviderError, IdentificationQuery
from app.providers.identification.pokemon_tcg_io import PokemonTCGIOProvider


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload


class FakeAsyncClient:
    """Stands in for httpx.AsyncClient, returning one canned response per call."""

    call_count = 0
    received_params: list[dict] = []

    def __init__(self, responses: list[FakeResponse]) -> None:
        self._responses = responses

    def __call__(self, *args, **kwargs) -> "FakeAsyncClient":
        return self

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args) -> None:
        return None

    async def get(self, *args, **kwargs) -> FakeResponse:
        FakeAsyncClient.received_params.append(kwargs.get("params", {}))
        response = self._responses[FakeAsyncClient.call_count]
        FakeAsyncClient.call_count += 1
        return response


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def instant_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(provider_module.asyncio, "sleep", instant_sleep)


@pytest.fixture(autouse=True)
def reset_call_count() -> None:
    FakeAsyncClient.call_count = 0
    FakeAsyncClient.received_params = []


def _install_fake_client(monkeypatch: pytest.MonkeyPatch, responses: list[FakeResponse]) -> None:
    monkeypatch.setattr(provider_module.httpx, "AsyncClient", FakeAsyncClient(responses))


async def _find(query: IdentificationQuery | None = None) -> list:
    provider = PokemonTCGIOProvider()
    result = await provider.find_candidates(
        query or IdentificationQuery(name="Pikachu", collector_number="25")
    )
    return result.candidates


def test_retries_on_5xx_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(
        monkeypatch,
        [
            FakeResponse(500),
            FakeResponse(502),
            FakeResponse(200, {"data": [{"id": "sv3pt5-25", "name": "Pikachu", "number": "25"}]}),
        ],
    )
    candidates = asyncio.run(_find())
    assert len(candidates) == 1
    assert FakeAsyncClient.call_count == 3


def test_gives_up_after_max_attempts_on_persistent_5xx(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(monkeypatch, [FakeResponse(500)] * provider_module.MAX_ATTEMPTS)
    with pytest.raises(IdentificationProviderError):
        asyncio.run(_find())
    assert FakeAsyncClient.call_count == provider_module.MAX_ATTEMPTS


def test_does_not_retry_on_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(monkeypatch, [FakeResponse(400, text="bad query")])
    with pytest.raises(IdentificationProviderError):
        asyncio.run(_find())
    assert FakeAsyncClient.call_count == 1


def test_falls_back_to_hyphenated_name_when_space_variant_finds_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Regression test: pokemontcg.io stores some cards as "Charizard-GX"
    # (hyphen), so a phrase search for "Charizard GX" (space) finds nothing.
    _install_fake_client(
        monkeypatch,
        [
            FakeResponse(200, {"data": []}),  # "Charizard GX" -> no match
            FakeResponse(200, {"data": [{"id": "sm3-20", "name": "Charizard-GX", "number": "20"}]}),
        ],
    )
    candidates = asyncio.run(_find(IdentificationQuery(name="Charizard GX", collector_number="20")))
    assert len(candidates) == 1
    assert candidates[0].name == "Charizard-GX"
    assert FakeAsyncClient.call_count == 2
    assert 'name:"Charizard GX"' in FakeAsyncClient.received_params[0]["q"]
    assert 'name:"Charizard-GX"' in FakeAsyncClient.received_params[1]["q"]


def test_falls_back_to_spaced_name_when_hyphen_variant_finds_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Regression test: the opposite direction -- "Charizard VMAX" is stored
    # with a space, so a user typing "Charizard-VMAX" (hyphen) finds nothing
    # until we retry with a space.
    _install_fake_client(
        monkeypatch,
        [
            FakeResponse(200, {"data": []}),  # "Charizard-VMAX" -> no match
            FakeResponse(
                200, {"data": [{"id": "swsh35-74", "name": "Charizard VMAX", "number": "74"}]}
            ),
        ],
    )
    candidates = asyncio.run(
        _find(IdentificationQuery(name="Charizard-VMAX", collector_number="74"))
    )
    assert len(candidates) == 1
    assert candidates[0].name == "Charizard VMAX"
    assert FakeAsyncClient.call_count == 2
    assert 'name:"Charizard-VMAX"' in FakeAsyncClient.received_params[0]["q"]
    assert 'name:"Charizard VMAX"' in FakeAsyncClient.received_params[1]["q"]


def test_does_not_retry_hyphenated_when_name_has_no_space(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(monkeypatch, [FakeResponse(200, {"data": []})])
    candidates = asyncio.run(_find(IdentificationQuery(name="Pikachu", collector_number="999")))
    assert candidates == []
    assert FakeAsyncClient.call_count == 1  # no pointless second call
