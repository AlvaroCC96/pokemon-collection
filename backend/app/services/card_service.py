import logging

from sqlalchemy.orm import Session

from app.models.card import Card
from app.schemas.card import CardCreate, CardUpdate

logger = logging.getLogger(__name__)


class CardNotFoundError(Exception):
    def __init__(self, card_id: int) -> None:
        self.card_id = card_id
        super().__init__(f"Card {card_id} not found")


def list_cards(db: Session) -> list[Card]:
    return list(db.query(Card).order_by(Card.created_at.desc()).all())


def get_card(db: Session, card_id: int) -> Card:
    card = db.get(Card, card_id)
    if card is None:
        raise CardNotFoundError(card_id)
    return card


def create_card(db: Session, data: CardCreate) -> Card:
    card = Card(**data.model_dump())
    db.add(card)
    db.commit()
    db.refresh(card)
    logger.info("Created card id=%s name=%s number=%s", card.id, card.name, card.collector_number)
    return card


def update_card(db: Session, card_id: int, data: CardUpdate) -> Card:
    card = get_card(db, card_id)
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(card, field, value)
    db.commit()
    db.refresh(card)
    logger.info("Updated card id=%s fields=%s", card.id, list(updates.keys()))
    return card


def delete_card(db: Session, card_id: int) -> None:
    card = get_card(db, card_id)
    db.delete(card)
    db.commit()
    logger.info("Deleted card id=%s", card_id)
