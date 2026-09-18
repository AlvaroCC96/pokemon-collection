from app.providers.identification.base import (
    IdentificationCandidate,
    IdentificationQuery,
    IdentificationResult,
)


class FakeIdentificationProvider:
    """In-memory IdentificationProvider for tests. Never calls the network."""

    name = "fake"

    def __init__(self, candidates: list[IdentificationCandidate] | None = None, has_more: bool = False) -> None:
        self.candidates = candidates or []
        self.has_more = has_more
        self.received_queries: list[IdentificationQuery] = []

    async def find_candidates(self, query: IdentificationQuery) -> IdentificationResult:
        self.received_queries.append(query)
        return IdentificationResult(candidates=self.candidates, has_more=self.has_more)
