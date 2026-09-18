from app.providers.price.base import PriceProviderResult, PriceQuery


class FakePriceProvider:
    """In-memory PriceProvider for tests. Never calls the network.

    By default every query gets `result`. For per-card behavior (e.g. one
    card failing during update-all while others succeed), set
    `results_by_name[card_name]` to either a PriceProviderResult or an
    Exception instance to raise.
    """

    name = "fake"

    def __init__(self, result: PriceProviderResult | None = None) -> None:
        self.result = result or PriceProviderResult(observations=[])
        self.results_by_name: dict[str, PriceProviderResult | Exception] = {}
        self.received_queries: list[PriceQuery] = []

    async def get_price(self, query: PriceQuery) -> PriceProviderResult:
        self.received_queries.append(query)
        override = self.results_by_name.get(query.name)
        if isinstance(override, Exception):
            raise override
        if override is not None:
            return override
        return self.result
