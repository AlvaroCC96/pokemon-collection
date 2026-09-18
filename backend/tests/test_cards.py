from fastapi.testclient import TestClient


def _create_card(client: TestClient, **overrides) -> dict:
    payload = {
        "name": "Charizard ex",
        "collector_number": "199/165",
        "quantity": 1,
    }
    payload.update(overrides)
    response = client.post("/api/cards", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_card_minimal_fields(client: TestClient) -> None:
    card = _create_card(client)
    assert card["name"] == "Charizard ex"
    assert card["collector_number"] == "199/165"
    assert card["quantity"] == 1
    assert card["set_name"] is None
    assert card["identified"] is False
    assert "id" in card


def test_create_card_missing_required_field_returns_422(client: TestClient) -> None:
    response = client.post("/api/cards", json={"collector_number": "1/1"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "VALIDATION_ERROR"


def test_create_card_invalid_quantity_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/cards", json={"name": "Pikachu", "collector_number": "58/102", "quantity": 0}
    )
    assert response.status_code == 422


def test_list_cards_includes_created_card(client: TestClient) -> None:
    card = _create_card(client, name="Pikachu", collector_number="58/102")
    response = client.get("/api/cards")
    assert response.status_code == 200
    ids = [c["id"] for c in response.json()]
    assert card["id"] in ids


def test_get_card_by_id(client: TestClient) -> None:
    card = _create_card(client, name="Blastoise", collector_number="2/102")
    response = client.get(f"/api/cards/{card['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Blastoise"


def test_get_missing_card_returns_404(client: TestClient) -> None:
    response = client.get("/api/cards/999999")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "CARD_NOT_FOUND"


def test_update_card(client: TestClient) -> None:
    card = _create_card(client, name="Venusaur", collector_number="3/102")
    response = client.put(f"/api/cards/{card['id']}", json={"quantity": 3, "set_name": "Base Set"})
    assert response.status_code == 200
    body = response.json()
    assert body["quantity"] == 3
    assert body["set_name"] == "Base Set"
    assert body["name"] == "Venusaur"


def test_update_missing_card_returns_404(client: TestClient) -> None:
    response = client.put("/api/cards/999999", json={"quantity": 2})
    assert response.status_code == 404


def test_delete_card(client: TestClient) -> None:
    card = _create_card(client, name="Mewtwo", collector_number="10/102")
    response = client.delete(f"/api/cards/{card['id']}")
    assert response.status_code == 204

    follow_up = client.get(f"/api/cards/{card['id']}")
    assert follow_up.status_code == 404


def test_delete_missing_card_returns_404(client: TestClient) -> None:
    response = client.delete("/api/cards/999999")
    assert response.status_code == 404
