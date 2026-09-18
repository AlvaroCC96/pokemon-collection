import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import cards, collection, health, prices
from app.core.config import get_settings
from app.core.db import init_db
from app.core.logging import setup_logging
from app.providers.identification.base import IdentificationProviderError
from app.providers.price.base import PriceProviderError
from app.services.card_service import CardNotFoundError
from app.services.price_service import PriceProviderNotConfiguredError, PriceSearchFailedError

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Initializing database")
    init_db()
    yield


app = FastAPI(title="Pokémon Collection API", version="0.1.0", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(cards.router, prefix="/api")
app.include_router(prices.router, prefix="/api")
app.include_router(prices.bulk_router, prefix="/api")
app.include_router(collection.router, prefix="/api")


@app.exception_handler(CardNotFoundError)
async def card_not_found_handler(request: Request, exc: CardNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": "CARD_NOT_FOUND", "message": str(exc)},
    )


@app.exception_handler(IdentificationProviderError)
async def identification_provider_error_handler(
    request: Request, exc: IdentificationProviderError
) -> JSONResponse:
    logger.error("Identification provider error: %s", exc)
    return JSONResponse(
        status_code=502,
        content={
            "error": "IDENTIFICATION_PROVIDER_ERROR",
            "message": "Could not reach the card identification service. Try again later.",
        },
    )


@app.exception_handler(PriceProviderError)
async def price_provider_error_handler(request: Request, exc: PriceProviderError) -> JSONResponse:
    logger.error("Price provider error: %s", exc)
    return JSONResponse(
        status_code=502,
        content={
            "error": "PRICE_PROVIDER_ERROR",
            "message": "Could not reach the price research service. Try again later.",
        },
    )


@app.exception_handler(PriceSearchFailedError)
async def price_search_failed_handler(request: Request, exc: PriceSearchFailedError) -> JSONResponse:
    logger.warning("Price search failed: %s", exc)
    return JSONResponse(
        status_code=422,
        content={"error": "PRICE_SEARCH_FAILED", "message": exc.user_message},
    )


@app.exception_handler(PriceProviderNotConfiguredError)
async def price_provider_not_configured_handler(
    request: Request, exc: PriceProviderNotConfiguredError
) -> JSONResponse:
    logger.error("Price provider not configured: %s", exc)
    return JSONResponse(
        status_code=503,
        content={
            "error": "PRICE_PROVIDER_NOT_CONFIGURED",
            "message": "OPENAI_API_KEY is not configured on the server.",
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "VALIDATION_ERROR", "message": str(exc.errors())},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "message": "Unexpected server error."},
    )
