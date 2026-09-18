from fastapi.testclient import TestClient


def create_card(client: TestClient, **overrides) -> dict:
    payload = {"name": "Charizard ex", "collector_number": "199/165", "quantity": 1}
    payload.update(overrides)
    response = client.post("/api/cards", json=payload)
    assert response.status_code == 201, response.text
    return response.json()
