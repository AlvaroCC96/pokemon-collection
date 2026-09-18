from fastapi.testclient import TestClient

from app.providers.price.base import PriceObservationResult, PriceProviderResult
from app.providers.price.fake import FakePriceProvider
from tests.helpers import create_card


def _run_update_price(
    client: TestClient, fake_price_provider: FakePriceProvider, card_id: int, price: float
) -> None:
    fake_price_provider.result = PriceProviderResult(
        observations=[
            PriceObservationResult(
                source_name="TCGmatch",
                source_url="https://tcgmatch.cl/x",
                observed_price=price,
                currency="CLP",
                market_region="CHILE",
            )
        ]
    )
    response = client.post(f"/api/cards/{card_id}/update-price")
    assert response.status_code == 200, response.text


def test_price_history_empty_for_card_without_snapshots(client: TestClient) -> None:
    card = create_card(client, name="Squirtle", collector_number="63/102")
    response = client.get(f"/api/cards/{card['id']}/prices")
    assert response.status_code == 200
    body = response.json()
    assert body["card_id"] == card["id"]
    assert body["snapshots"] == []


def test_price_history_missing_card_returns_404(client: TestClient) -> None:
    response = client.get("/api/cards/999999/prices")
    assert response.status_code == 404
    assert response.json()["error"] == "CARD_NOT_FOUND"


def test_price_history_does_not_require_openai_configured(client: TestClient) -> None:
    # No fake_price_provider override here -> if this endpoint ever called
    # get_price_provider(), it would blow up with PriceProviderNotConfiguredError
    # since no OPENAI_API_KEY is set in the test environment.
    card = create_card(client, name="Bulbasaur", collector_number="1/102")
    response = client.get(f"/api/cards/{card['id']}/prices")
    assert response.status_code == 200


def test_price_history_orders_snapshots_chronologically_and_computes_change(
    client: TestClient, fake_price_provider: FakePriceProvider
) -> None:
    card = create_card(client, name="Charizard ex", collector_number="199/165")

    _run_update_price(client, fake_price_provider, card["id"], 200000)
    _run_update_price(client, fake_price_provider, card["id"], 220000)  # +10%
    _run_update_price(client, fake_price_provider, card["id"], 198000)  # -10%

    response = client.get(f"/api/cards/{card['id']}/prices")
    assert response.status_code == 200
    snapshots = response.json()["snapshots"]
    assert len(snapshots) == 3

    # chronological order: oldest first
    assert [s["estimated_price"] for s in snapshots] == [200000, 220000, 198000]

    first, second, third = snapshots
    assert first["previous_price"] is None
    assert first["price_change"] is None
    assert first["price_change_percent"] is None

    assert second["previous_price"] == 200000
    assert second["price_change"] == 20000
    assert second["price_change_percent"] == 10.0

    assert third["previous_price"] == 220000
    assert third["price_change"] == -22000
    assert third["price_change_percent"] == -10.0

    # each snapshot carries its own observations for traceability
    assert len(first["observations"]) == 1
    assert first["observations"][0]["source_name"] == "TCGmatch"


def test_price_history_only_compares_compatible_snapshots(
    client: TestClient, fake_price_provider: FakePriceProvider
) -> None:
    card = create_card(client, name="Venusaur", collector_number="3/102")

    # CLP/CHILE snapshot
    _run_update_price(client, fake_price_provider, card["id"], 100000)

    # INTERNATIONAL/USD snapshot -- not comparable to the CLP one above
    fake_price_provider.result = PriceProviderResult(
        observations=[
            PriceObservationResult(
                source_name="TCGplayer",
                observed_price=50.0,
                currency="USD",
                market_region="INTERNATIONAL",
            )
        ]
    )
    response = client.post(f"/api/cards/{card['id']}/update-price")
    assert response.status_code == 200, response.text

    history = client.get(f"/api/cards/{card['id']}/prices").json()
    snapshots = history["snapshots"]
    assert len(snapshots) == 2
    # the USD/INTERNATIONAL snapshot has no compatible predecessor
    assert snapshots[1]["currency"] == "USD"
    assert snapshots[1]["previous_price"] is None
