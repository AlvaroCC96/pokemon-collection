from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.card import CardCreate, CardResponse, CardUpdate
from app.schemas.identification import IdentifyOverride, IdentifyRequest, IdentifyResponse
from app.services import card_service, identification_service
from app.services.identification_service import (
    IdentificationProviderRegistry,
    get_identification_providers,
)

router = APIRouter(prefix="/cards", tags=["cards"])


@router.post("/identify", response_model=IdentifyResponse)
async def identify_card(
    payload: IdentifyRequest,
    registry: IdentificationProviderRegistry = Depends(get_identification_providers),
) -> IdentifyResponse:
    return await identification_service.identify(payload, registry)


@router.get("", response_model=list[CardResponse])
def list_cards(db: Session = Depends(get_db)) -> list[CardResponse]:
    return card_service.list_cards(db)


@router.get("/{card_id}", response_model=CardResponse)
def get_card(card_id: int, db: Session = Depends(get_db)) -> CardResponse:
    return card_service.get_card(db, card_id)


@router.post("", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
def create_card(payload: CardCreate, db: Session = Depends(get_db)) -> CardResponse:
    return card_service.create_card(db, payload)


@router.put("/{card_id}", response_model=CardResponse)
def update_card(card_id: int, payload: CardUpdate, db: Session = Depends(get_db)) -> CardResponse:
    return card_service.update_card(db, card_id, payload)


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(card_id: int, db: Session = Depends(get_db)) -> None:
    card_service.delete_card(db, card_id)


@router.post("/{card_id}/identify", response_model=IdentifyResponse)
async def identify_existing_card(
    card_id: int,
    payload: IdentifyOverride | None = None,
    db: Session = Depends(get_db),
    registry: IdentificationProviderRegistry = Depends(get_identification_providers),
) -> IdentifyResponse:
    return await identification_service.identify_existing_card(db, card_id, payload, registry)
