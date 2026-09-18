from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.stats import CollectionStatsResponse
from app.services import stats_service

router = APIRouter(prefix="/collection", tags=["collection"])


@router.get("/stats", response_model=CollectionStatsResponse)
def get_collection_stats(db: Session = Depends(get_db)) -> CollectionStatsResponse:
    return stats_service.get_collection_stats(db)
