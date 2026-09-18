from fastapi.testclient import TestClient

from app.providers.price.base import PriceObservationResult, PriceProviderResult
from app.providers.price.fake import FakePriceProvider
from tests.helpers import create_card


def _price_card(
    client: TestClient,
    fake_price_provider: FakePriceProvider,
    card_id: int,
    price: float,
    currency: str = "CLP",
    market_region: str = "CHILE",
) -> None:
    fake_price_provider.result = PriceProviderResult(
        observations=[
            PriceObservationResult(
                source_name="TCGmatch",
                observed_price=price,
                currency=currency,
                market_region=market_region,
            )
        ]
    )
    response = client.post(f"/api/cards/{card_id}/update-price")
    assert response.status_code == 200, response.text


def test_stats_empty_collection(client: TestClient, clean_db: None) -> None:
    response = client.get("/api/collection/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["distinct_card_count"] == 0
    assert body["total_card_count"] == 0
    assert body["cards_with_valuation"] == 0
    assert body["cards_without_valuation"] == 0
    assert body["total_estimated_value"] == 0
    assert body["most_valuable_card"] is None
    assert body["top_valuable_cards"] == []
    assert body["last_price_update"] is None


def test_stats_does_not_require_openai_configured(client: TestClient, clean_db: None) -> None:
    create_card(client, name="Bulbasaur", collector_number="1/102")
    response = client.get("/api/collection/stats")
    assert response.status_code == 200


def test_stats_counts_cards_with_and_without_valuation(
    client: TestClient, clean_db: None, fake_price_provider: FakePriceProvider
) -> None:
    priced = create_card(client, name="Charizard ex", collector_number="199/165")
    create_card(client, name="Squirtle", collector_number="63/102")  # never priced

    _price_card(client, fake_price_provider, priced["id"], 100000)

    body = client.get("/api/collection/stats").json()
    assert body["distinct_card_count"] == 2
    assert body["cards_with_valuation"] == 1
    assert body["cards_without_valuation"] == 1


def test_stats_total_card_count_uses_quantity(client: TestClient, clean_db: None) -> None:
    create_card(client, name="Pikachu", collector_number="58/102", quantity=3)
    create_card(client, name="Bulbasaur", collector_number="1/102", quantity=2)

    body = client.get("/api/collection/stats").json()
    assert body["distinct_card_count"] == 2
    assert body["total_card_count"] == 5


def test_stats_total_value_multiplies_by_quantity(
    client: TestClient, clean_db: None, fake_price_provider: FakePriceProvider
) -> None:
    card = create_card(client, name="Charizard ex", collector_number="199/165", quantity=3)
    _price_card(client, fake_price_provider, card["id"], 100000)

    body = client.get("/api/collection/stats").json()
    assert body["total_estimated_value"] == 300000
    assert body["most_valuable_card"]["total_value"] == 300000
    assert body["most_valuable_card"]["card_id"] == card["id"]


def test_stats_does_not_mix_clp_and_usd(
    client: TestClient, clean_db: None, fake_price_provider: FakePriceProvider
) -> None:
    clp_card = create_card(client, name="Charizard ex", collector_number="199/165")
    usd_card = create_card(client, name="Blastoise", collector_number="2/102")

    _price_card(client, fake_price_provider, clp_card["id"], 100000, currency="CLP", market_region="CHILE")
    _price_card(
        client, fake_price_provider, usd_card["id"], 50.0, currency="USD", market_region="INTERNATIONAL"
    )

    body = client.get("/api/collection/stats").json()
    assert body["currency"] == "CLP"
    assert body["total_estimated_value"] == 100000  # USD card excluded from the CLP total

    other_totals = {t["currency"]: t for t in body["other_currency_totals"]}
    assert other_totals["USD"]["total_value"] == 50.0
    assert other_totals["USD"]["card_count"] == 1

    # the USD card must not appear in the CLP top-valuable ranking
    top_ids = {c["card_id"] for c in body["top_valuable_cards"]}
    assert usd_card["id"] not in top_ids


def test_stats_most_valuable_and_top_valuable_ordering(
    client: TestClient, clean_db: None, fake_price_provider: FakePriceProvider
) -> None:
    cheap = create_card(client, name="Squirtle", collector_number="63/102")
    expensive = create_card(client, name="Charizard ex", collector_number="199/165")

    _price_card(client, fake_price_provider, cheap["id"], 5000)
    _price_card(client, fake_price_provider, expensive["id"], 400000)

    body = client.get("/api/collection/stats").json()
    assert body["most_valuable_card"]["card_id"] == expensive["id"]
    assert body["top_valuable_cards"][0]["card_id"] == expensive["id"]
    assert body["top_valuable_cards"][1]["card_id"] == cheap["id"]


def test_stats_last_price_update_is_most_recent_checked_at(
    client: TestClient, clean_db: None, fake_price_provider: FakePriceProvider
) -> None:
    card = create_card(client, name="Charizard ex", collector_number="199/165")
    _price_card(client, fake_price_provider, card["id"], 100000)

    body = client.get("/api/collection/stats").json()
    assert body["last_price_update"] is not None


def test_stats_includes_price_change_percent_on_summary(
    client: TestClient, clean_db: None, fake_price_provider: FakePriceProvider
) -> None:
    card = create_card(client, name="Charizard ex", collector_number="199/165")
    _price_card(client, fake_price_provider, card["id"], 100000)
    _price_card(client, fake_price_provider, card["id"], 110000)  # +10%

    body = client.get("/api/collection/stats").json()
    assert body["most_valuable_card"]["price_change_percent"] == 10.0
