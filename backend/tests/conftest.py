import os
import tempfile
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

db_fd, db_path = tempfile.mkstemp(suffix=".db")
os.close(db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

from app.main import app  # noqa: E402  must import after DATABASE_URL is set


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client

    from app.core.db import engine

    engine.dispose()
    try:
        os.remove(db_path)
    except PermissionError:
        pass  # best-effort cleanup; Windows may still hold a brief file lock


@pytest.fixture()
def clean_db(client: TestClient) -> Iterator[None]:
    """Wipes cards/snapshots/observations before a test that needs a known,
    isolated state (e.g. collection-wide stats) -- the `client` fixture is
    session-scoped and shares one DB across the whole test run, so other test
    files' cards would otherwise pollute aggregate assertions."""
    from app.core.db import SessionLocal
    from app.models.card import Card
    from app.models.price import CardPriceSnapshot, PriceObservation

    def _wipe() -> None:
        session = SessionLocal()
        try:
            session.query(PriceObservation).delete()
            session.query(CardPriceSnapshot).delete()
            session.query(Card).delete()
            session.commit()
        finally:
            session.close()

    _wipe()
    yield
    _wipe()


@pytest.fixture()
def fake_price_provider():
    from app.main import app as fastapi_app
    from app.providers.price.fake import FakePriceProvider
    from app.services.price_service import get_price_provider

    provider = FakePriceProvider()
    fastapi_app.dependency_overrides[get_price_provider] = lambda: provider
    yield provider
    del fastapi_app.dependency_overrides[get_price_provider]
