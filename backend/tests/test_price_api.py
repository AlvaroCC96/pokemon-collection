from fastapi.testclient import TestClient

from app.providers.price.base import PriceObservationResult, PriceProviderResult
from app.providers.price.fake import FakePriceProvider
from tests.helpers import create_card as _create_card


def test_update_price_chile_scope(
    client: TestClient, fake_price_provider: FakePriceProvider
) -> None:
    card = _create_card(client)
    fake_price_provider.result = PriceProviderResult(
        observations=[
            PriceObservationResult(
                source_name="TCGmatch",
                source_url="https://tcgmatch.cl/x",
                observed_price=270000,
                currency="CLP",
                market_region="CHILE",
                matched_confidence=0.9,
            ),
            PriceObservationResult(
                source_name="AFK Store",
                source_url="https://afkstore.cl/x",
                observed_price=450000,
                currency="CLP",
                market_region="CHILE",
                matched_confidence=0.85,
            ),
            PriceObservationResult(
                source_name="OasisGames",
                source_url="https://oasisgames.cl/x",
                observed_price=421520,
                currency="CLP",
                market_region="CHILE",
                matched_confidence=0.8,
            ),
        ]
    )

    response = client.post(f"/api/cards/{card['id']}/update-price")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valuation"]["market_scope"] == "CHILE"
    assert body["valuation"]["currency"] == "CLP"
    assert body["valuation"]["estimated"] == 421520
    assert len(body["sources"]) == 3
    assert all(not s["is_outlier"] for s in body["sources"])
    assert all(s["included_in_estimate"] for s in body["sources"])
    assert body["card"]["name"] == "Charizard ex"


def test_update_price_falls_back_to_international_without_chile_sources(
    client: TestClient, fake_price_provider: FakePriceProvider
) -> None:
    card = _create_card(client, name="Pikachu", collector_number="58/102")
    fake_price_provider.result = PriceProviderResult(
        observations=[
            PriceObservationResult(
                source_name="TCGplayer",
                source_url="https://tcgplayer.com/x",
                observed_price=10.0,
                currency="USD",
                market_region="INTERNATIONAL",
            ),
            PriceObservationResult(
                source_name="Cardmarket",
                source_url="https://cardmarket.com/x",
                observed_price=9.0,
                currency="EUR",
                market_region="INTERNATIONAL",
            ),
            PriceObservationResult(
                source_name="PriceCharting",
                source_url="https://pricecharting.com/x",
                observed_price=11.0,
                currency="USD",
                market_region="INTERNATIONAL",
            ),
        ]
    )

    response = client.post(f"/api/cards/{card['id']}/update-price")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valuation"]["market_scope"] == "INTERNATIONAL"
    assert body["valuation"]["currency"] == "USD"
    assert body["valuation"]["estimated"] == 10.5

    sources_by_currency = {s["currency"]: s for s in body["sources"]}
    assert sources_by_currency["EUR"]["included_in_estimate"] is False
    assert sources_by_currency["EUR"]["is_outlier"] is False  # different currency, not an outlier


def test_update_price_flags_outlier(
    client: TestClient, fake_price_provider: FakePriceProvider
) -> None:
    card = _create_card(client, name="Mewtwo", collector_number="10/102")
    fake_price_provider.result = PriceProviderResult(
        observations=[
            PriceObservationResult(
                source_name="A", observed_price=100000, currency="CLP", market_region="CHILE"
            ),
            PriceObservationResult(
                source_name="B", observed_price=105000, currency="CLP", market_region="CHILE"
            ),
            PriceObservationResult(
                source_name="C", observed_price=98000, currency="CLP", market_region="CHILE"
            ),
            PriceObservationResult(
                source_name="Scalper",
                observed_price=5000000,
                currency="CLP",
                market_region="CHILE",
            ),
        ]
    )

    response = client.post(f"/api/cards/{card['id']}/update-price")
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["sources"]) == 4

    scalper = next(s for s in body["sources"] if s["source_name"] == "Scalper")
    assert scalper["is_outlier"] is True
    assert scalper["included_in_estimate"] is False
    assert body["valuation"]["estimated"] == 100000


def test_update_price_no_observations_returns_price_search_failed(
    client: TestClient, fake_price_provider: FakePriceProvider
) -> None:
    card = _create_card(client, name="Squirtle", collector_number="63/102")
    fake_price_provider.result = PriceProviderResult(observations=[])

    response = client.post(f"/api/cards/{card['id']}/update-price")
    assert response.status_code == 422
    assert response.json()["error"] == "PRICE_SEARCH_FAILED"


def test_update_price_missing_card_returns_404(
    client: TestClient, fake_price_provider: FakePriceProvider
) -> None:
    response = client.post("/api/cards/999999/update-price")
    assert response.status_code == 404
    assert response.json()["error"] == "CARD_NOT_FOUND"


def test_update_price_without_language_mixes_variants_as_before(
    client: TestClient, fake_price_provider: FakePriceProvider
) -> None:
    card = _create_card(client, name="Charizard ex", collector_number="199/165")
    fake_price_provider.result = PriceProviderResult(
        observations=[
            PriceObservationResult(
                source_name="TCGmatch ES",
                observed_price=220000,
                currency="CLP",
                market_region="CHILE",
                language="ES",
            ),
            PriceObservationResult(
                source_name="TCGmatch EN",
                observed_price=200000,
                currency="CLP",
                market_region="CHILE",
                language="EN",
            ),
        ]
    )

    response = client.post(f"/api/cards/{card['id']}/update-price")
    assert response.status_code == 200, response.text
    body = response.json()
    # card.language is unset -> current scope keeps mixing both variants
    assert body["valuation"]["estimated"] == 210000
    assert all(s["included_in_estimate"] for s in body["sources"])


def test_update_price_with_language_excludes_other_language_from_estimate(
    client: TestClient, fake_price_provider: FakePriceProvider
) -> None:
    card = _create_card(
        client, name="Charizard ex", collector_number="199/165", language="Español"
    )
    fake_price_provider.result = PriceProviderResult(
        observations=[
            PriceObservationResult(
                source_name="TCGmatch ES",
                observed_price=220000,
                currency="CLP",
                market_region="CHILE",
                language="ES",
            ),
            PriceObservationResult(
                source_name="TCGmatch EN",
                observed_price=200000,
                currency="CLP",
                market_region="CHILE",
                language="EN",
            ),
            PriceObservationResult(
                source_name="Unknown-language listing",
                observed_price=210000,
                currency="CLP",
                market_region="CHILE",
                language=None,
            ),
        ]
    )

    response = client.post(f"/api/cards/{card['id']}/update-price")
    assert response.status_code == 200, response.text
    body = response.json()

    by_name = {s["source_name"]: s for s in body["sources"]}
    assert by_name["TCGmatch ES"]["included_in_estimate"] is True
    assert by_name["TCGmatch EN"]["included_in_estimate"] is False  # different language, excluded
    assert by_name["Unknown-language listing"]["included_in_estimate"] is True  # unknown, kept

    # estimate should only reflect the ES + unknown-language observations (220000, 210000)
    assert body["valuation"]["estimated"] == 215000
    assert by_name["TCGmatch EN"]["is_outlier"] is False  # excluded by language, not by outlier logic
    # the EN observation is still saved for traceability, just outside the estimate
    assert len(body["sources"]) == 3


def test_update_price_language_with_no_matching_observations_fails(
    client: TestClient, fake_price_provider: FakePriceProvider
) -> None:
    card = _create_card(
        client, name="Charizard ex", collector_number="199/165", language="Español"
    )
    fake_price_provider.result = PriceProviderResult(
        observations=[
            PriceObservationResult(
                source_name="TCGmatch EN",
                observed_price=200000,
                currency="CLP",
                market_region="CHILE",
                language="EN",
            ),
        ]
    )

    response = client.post(f"/api/cards/{card['id']}/update-price")
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "PRICE_SEARCH_FAILED"
    assert "Español" in body["message"]  # specific reason, not a generic message


def test_update_price_ingles_language_matches_en_observations(
    client: TestClient, fake_price_provider: FakePriceProvider
) -> None:
    # Regression test for a real bug: a card with language "Ingles" (no accent,
    # as typed by a user) failed to match observations tagged "EN" because the
    # old matching logic only compared the first two letters ("in" vs "en").
    card = _create_card(
        client, name="Charizard ex", collector_number="223/197", language="Ingles"
    )
    fake_price_provider.result = PriceProviderResult(
        observations=[
            PriceObservationResult(
                source_name="TCGplayer",
                observed_price=300000,
                currency="CLP",
                market_region="CHILE",
                language="EN",
            ),
        ]
    )

    response = client.post(f"/api/cards/{card['id']}/update-price")
    assert response.status_code == 200, response.text
    assert response.json()["valuation"]["estimated"] == 300000


def test_update_price_sends_card_identifiers_to_provider(
    client: TestClient, fake_price_provider: FakePriceProvider
) -> None:
    card = _create_card(
        client,
        name="Blastoise",
        collector_number="2/102",
        set_name="Base Set",
        language="Español",
    )
    fake_price_provider.result = PriceProviderResult(
        observations=[
            PriceObservationResult(
                source_name="A", observed_price=1000, currency="CLP", market_region="CHILE"
            )
        ]
    )
    client.post(f"/api/cards/{card['id']}/update-price")

    sent_query = fake_price_provider.received_queries[0]
    assert sent_query.name == "Blastoise"
    assert sent_query.collector_number == "2/102"
    assert sent_query.set_name == "Base Set"
    assert sent_query.language == "Español"
