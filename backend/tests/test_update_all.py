from fastapi.testclient import TestClient

from app.providers.price.base import (
    PriceObservationResult,
    PriceProviderError,
    PriceProviderResult,
)
from app.providers.price.fake import FakePriceProvider
from tests.helpers import create_card


def _ok_result(price: float = 100000) -> PriceProviderResult:
    return PriceProviderResult(
        observations=[
            PriceObservationResult(
                source_name="TCGmatch",
                observed_price=price,
                currency="CLP",
                market_region="CHILE",
            )
        ]
    )


def test_update_all_empty_collection(
    client: TestClient, clean_db: None, fake_price_provider: FakePriceProvider
) -> None:
    response = client.post("/api/prices/update-all")
    assert response.status_code == 200
    body = response.json()
    assert body == {"total": 0, "updated": 0, "failed": 0, "details": []}


def test_update_all_updates_every_card(
    client: TestClient, clean_db: None, fake_price_provider: FakePriceProvider
) -> None:
    card_a = create_card(client, name="Charizard ex", collector_number="199/165")
    card_b = create_card(client, name="Pikachu", collector_number="58/102")
    fake_price_provider.result = _ok_result()

    response = client.post("/api/prices/update-all")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["updated"] == 2
    assert body["failed"] == 0

    updated_ids = {d["card_id"] for d in body["details"] if d["status"] == "updated"}
    assert updated_ids == {card_a["id"], card_b["id"]}

    # each card should now have a snapshot
    for card in (card_a, card_b):
        history = client.get(f"/api/cards/{card['id']}/prices").json()
        assert len(history["snapshots"]) == 1


def test_update_all_one_card_failing_does_not_abort_the_rest(
    client: TestClient, clean_db: None, fake_price_provider: FakePriceProvider
) -> None:
    good = create_card(client, name="Charizard ex", collector_number="199/165")
    bad = create_card(client, name="Squirtle", collector_number="63/102")

    fake_price_provider.result = _ok_result()
    fake_price_provider.results_by_name["Squirtle"] = PriceProviderError("simulated failure")

    response = client.post("/api/prices/update-all")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["updated"] == 1
    assert body["failed"] == 1

    details_by_id = {d["card_id"]: d for d in body["details"]}
    assert details_by_id[good["id"]]["status"] == "updated"
    assert details_by_id[bad["id"]]["status"] == "failed"
    assert details_by_id[bad["id"]]["error"] == "PRICE_PROVIDER_ERROR"

    # the failing card must not have gotten a snapshot
    bad_history = client.get(f"/api/cards/{bad['id']}/prices").json()
    assert bad_history["snapshots"] == []

    # the good card did
    good_history = client.get(f"/api/cards/{good['id']}/prices").json()
    assert len(good_history["snapshots"]) == 1


def test_update_all_reports_price_search_failed_per_card(
    client: TestClient, clean_db: None, fake_price_provider: FakePriceProvider
) -> None:
    card = create_card(client, name="Charizard ex", collector_number="199/165")
    fake_price_provider.result = PriceProviderResult(observations=[])

    response = client.post("/api/prices/update-all")
    body = response.json()
    assert body["failed"] == 1
    assert body["details"][0]["error"] == "PRICE_SEARCH_FAILED"
    assert body["details"][0]["card_id"] == card["id"]
