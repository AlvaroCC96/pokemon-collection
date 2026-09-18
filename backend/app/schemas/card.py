from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CardBase(BaseModel):
    name: str = Field(min_length=1)
    collector_number: str = Field(min_length=1)
    set_name: str | None = None
    language: str | None = None
    rarity: str | None = None
    image_url: str | None = None
    quantity: int = Field(default=1, ge=1)


class CardCreate(CardBase):
    pass


class CardUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    collector_number: str | None = Field(default=None, min_length=1)
    set_name: str | None = None
    language: str | None = None
    rarity: str | None = None
    image_url: str | None = None
    quantity: int | None = Field(default=None, ge=1)


class CardResponse(CardBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_card_id: str | None
    identified: bool
    created_at: datetime
    updated_at: datetime
