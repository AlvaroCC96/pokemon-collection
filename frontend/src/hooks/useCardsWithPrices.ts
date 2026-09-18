import { useCallback, useEffect, useState } from 'react'
import { ApiError, cardsApi } from '../api'
import type { Card, PriceSnapshot } from '../api'

export interface CardWithLatestPrice {
  card: Card
  latestSnapshot: PriceSnapshot | null
}

/** GET /api/cards has no embedded price -- for a personal collection's size
 * (tens to a couple hundred cards, all local SQLite reads) fetching each
 * card's history client-side is simple and cheap enough. If the collection
 * grows a lot, the backend could later expose the latest price inline; not
 * worth that change yet. */
export function useCardsWithPrices() {
  const [items, setItems] = useState<CardWithLatestPrice[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    cardsApi
      .list()
      .then(async (cards: Card[]) => {
        const withPrices = await Promise.all(
          cards.map(async (card): Promise<CardWithLatestPrice> => {
            try {
              const history = await cardsApi.priceHistory(card.id)
              const latest: PriceSnapshot | undefined = history.snapshots.at(-1)
              return { card, latestSnapshot: latest ?? null }
            } catch {
              return { card, latestSnapshot: null }
            }
          }),
        )
        if (!cancelled) {
          setItems(withPrices)
          setLoading(false)
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor.')
        setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])

  return { items, loading, error, refetch: load }
}
