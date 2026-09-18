from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.providers.price.base import PriceProvider
from app.schemas.price import CardPriceHistoryResponse, UpdateAllResponse, UpdatePriceResponse
from app.services import price_service
from app.services.price_service import get_price_provider

# Card-scoped price endpoints, mounted under /api/cards.
router = APIRouter(prefix="/cards", tags=["prices"])

# Collection-wide price endpoints, mounted under /api/prices.
bulk_router = APIRouter(prefix="/prices", tags=["prices"])


@router.post("/{card_id}/update-price", response_model=UpdatePriceResponse)
async def update_card_price(
    card_id: int,
    db: Session = Depends(get_db),
    provider: PriceProvider = Depends(get_price_provider),
) -> UpdatePriceResponse:
    return await price_service.update_price(db, card_id, provider)


@router.get("/{card_id}/prices", response_model=CardPriceHistoryResponse)
def get_card_price_history(card_id: int, db: Session = Depends(get_db)) -> CardPriceHistoryResponse:
    return price_service.get_price_history(db, card_id)


@bulk_router.post("/update-all", response_model=UpdateAllResponse)
async def update_all_prices(
    db: Session = Depends(get_db),
    provider: PriceProvider = Depends(get_price_provider),
) -> UpdateAllResponse:
    return await price_service.update_all_prices(db, provider)
