from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.providers.identification.base import IdentificationCandidate
from app.providers.identification.fake import FakeIdentificationProvider
from app.services.identification_service import (
    IdentificationProviderRegistry,
    get_identification_providers,
)

CHARIZARD_CANDIDATE = IdentificationCandidate(
    external_id="sv3pt5-199",
    name="Charizard ex",
    collector_number="199",
    set_name="151",
    rarity="Special Illustration Rare",
    image_url="https://images.pokemontcg.io/sv3pt5/199_hires.png",
)

PIKACHU_CANDIDATES = [
    IdentificationCandidate(
        external_id="basep-25",
        name="Flying Pikachu",
        collector_number="25",
        set_name="Wizards Black Star Promos",
        rarity="Promo",
        image_url="https://images.pokemontcg.io/basep/25_hires.png",
    ),
    IdentificationCandidate(
        external_id="mcd21-25",
        name="Pikachu",
        collector_number="25",
        set_name="McDonald's Collection 2021",
        rarity=None,
        image_url="https://images.pokemontcg.io/mcd21/25_hires.png",
    ),
    IdentificationCandidate(
        external_id="sv3pt5-25",
        name="Pikachu",
        collector_number="25",
        set_name="151",
        rarity="Common",
        image_url="https://images.pokemontcg.io/sv3pt5/25_hires.png",
    ),
]


@pytest.fixture()
def fake_provider() -> Iterator[FakeIdentificationProvider]:
    """Overrides the `western` (ES/EN/language=null) slot -- these tests
    don't set a language, so they exercise that routing path."""
    provider = FakeIdentificationProvider()
    registry = IdentificationProviderRegistry(
        western=provider,
        japanese=FakeIdentificationProvider(),
        traditional_chinese=FakeIdentificationProvider(),
        simplified_chinese=FakeIdentificationProvider(),
    )
    app.dependency_overrides[get_identification_providers] = lambda: registry
    yield provider
    del app.dependency_overrides[get_identification_providers]


def test_identify_not_found(client: TestClient, fake_provider: FakeIdentificationProvider) -> None:
    fake_provider.candidates = []
    response = client.post(
        "/api/cards/identify",
        json={"name": "Charizard", "collector_number": "9999"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_found"
    assert body["candidates"] == []


def test_identify_single_match(client: TestClient, fake_provider: FakeIdentificationProvider) -> None:
    fake_provider.candidates = [CHARIZARD_CANDIDATE]
    response = client.post(
        "/api/cards/identify",
        json={"name": "Charizard ex", "collector_number": "199/165"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "single_match"
    assert len(body["candidates"]) == 1
    assert body["candidates"][0]["set_name"] == "151"
    assert body["candidates"][0]["external_id"] == "sv3pt5-199"

    sent_query = fake_provider.received_queries[0]
    assert sent_query.name == "Charizard ex"
    assert sent_query.collector_number == "199/165"


def test_identify_multiple_matches(
    client: TestClient, fake_provider: FakeIdentificationProvider
) -> None:
    fake_provider.candidates = PIKACHU_CANDIDATES
    response = client.post(
        "/api/cards/identify",
        json={"name": "Pikachu", "collector_number": "25"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "multiple_matches"
    assert len(body["candidates"]) == 3
    set_names = {c["set_name"] for c in body["candidates"]}
    assert set_names == {"Wizards Black Star Promos", "McDonald's Collection 2021", "151"}


def test_identify_requires_name_and_number(client: TestClient) -> None:
    response = client.post("/api/cards/identify", json={"collector_number": "199/165"})
    assert response.status_code == 422


def test_reidentify_existing_card_uses_stored_fields(
    client: TestClient, fake_provider: FakeIdentificationProvider
) -> None:
    create_response = client.post(
        "/api/cards",
        json={"name": "Charizard ex", "collector_number": "199/165"},
    )
    card_id = create_response.json()["id"]

    fake_provider.candidates = [CHARIZARD_CANDIDATE]
    response = client.post(f"/api/cards/{card_id}/identify")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "single_match"

    sent_query = fake_provider.received_queries[-1]
    assert sent_query.name == "Charizard ex"
    assert sent_query.collector_number == "199/165"


def test_reidentify_existing_card_with_override(
    client: TestClient, fake_provider: FakeIdentificationProvider
) -> None:
    create_response = client.post(
        "/api/cards",
        json={"name": "Pikachu", "collector_number": "58/102"},
    )
    card_id = create_response.json()["id"]

    fake_provider.candidates = PIKACHU_CANDIDATES
    response = client.post(
        f"/api/cards/{card_id}/identify",
        json={"collector_number": "25"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "multiple_matches"

    sent_query = fake_provider.received_queries[-1]
    assert sent_query.name == "Pikachu"  # not overridden, falls back to stored value
    assert sent_query.collector_number == "25"  # overridden


def test_reidentify_missing_card_returns_404(
    client: TestClient, fake_provider: FakeIdentificationProvider
) -> None:
    response = client.post("/api/cards/999999/identify")
    assert response.status_code == 404
    assert response.json()["error"] == "CARD_NOT_FOUND"


def test_identify_response_includes_has_more(
    client: TestClient, fake_provider: FakeIdentificationProvider
) -> None:
    fake_provider.candidates = [CHARIZARD_CANDIDATE]
    fake_provider.has_more = True
    response = client.post(
        "/api/cards/identify", json={"name": "Charizard ex", "collector_number": "199/165"}
    )
    assert response.status_code == 200
    assert response.json()["has_more"] is True


def test_identify_defaults_has_more_to_false(
    client: TestClient, fake_provider: FakeIdentificationProvider
) -> None:
    fake_provider.candidates = [CHARIZARD_CANDIDATE]
    response = client.post(
        "/api/cards/identify", json={"name": "Charizard ex", "collector_number": "199/165"}
    )
    assert response.json()["has_more"] is False


def test_identify_forwards_page_param_to_provider(
    client: TestClient, fake_provider: FakeIdentificationProvider
) -> None:
    fake_provider.candidates = []
    client.post(
        "/api/cards/identify",
        json={"name": "Pikachu", "collector_number": "25", "page": 3},
    )
    assert fake_provider.received_queries[0].page == 3
