import logging

from app.providers.identification.base import (
    IdentificationProvider,
    IdentificationProviderError,
    IdentificationQuery,
    IdentificationResult,
)

logger = logging.getLogger(__name__)


class CompositeIdentificationProvider:
    """Tries each provider in order, returning the first non-empty result
    (its `has_more` is forwarded as-is, so a subsequent `page=2` request
    naturally lands back on the SAME provider as long as it keeps finding
    results -- see ARCHITECTURE.md for why this doesn't need special-casing
    for pagination).

    A provider that errors out is logged and skipped (not fatal) so one
    flaky source doesn't block the others. Only if EVERY provider fails with
    an error (none of them completed successfully, even with zero results)
    does this raise -- that's the honest signal that something is actually
    broken, as opposed to a card that legitimately isn't in any catalog.
    """

    name = "composite"

    def __init__(self, providers: list[IdentificationProvider]) -> None:
        self._providers = providers

    async def find_candidates(self, query: IdentificationQuery) -> IdentificationResult:
        last_error: Exception | None = None
        any_success = False

        for provider in self._providers:
            try:
                result = await provider.find_candidates(query)
            except IdentificationProviderError as exc:
                logger.warning("%s failed (%s); trying next identification provider", provider.name, exc)
                last_error = exc
                continue

            any_success = True
            if result.candidates:
                logger.info("%s found %d candidate(s)", provider.name, len(result.candidates))
                return result
            logger.info("%s found no match, trying next identification provider", provider.name)

        if not any_success and last_error:
            raise last_error
        return IdentificationResult(candidates=[], has_more=False)
