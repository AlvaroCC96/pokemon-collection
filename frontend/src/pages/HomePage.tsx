import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { collectionApi } from '../api'
import { CardCarousel } from '../components/CardCarousel'
import { CardGrid } from '../components/CardGrid'
import { CardCarouselSkeleton, CardGridSkeleton } from '../components/CardGridSkeleton'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { ModeTag, PokedexHeader, PokedexScreen, PokedexShell } from '../components/Pokedex'
import { StatsHeader } from '../components/StatsHeader'
import { StatsHeaderSkeleton } from '../components/StatsHeaderSkeleton'
import { Toolbar } from '../components/Toolbar'
import { useAsync } from '../hooks/useAsync'
import { useCardsWithPrices } from '../hooks/useCardsWithPrices'
import { useMediaQuery } from '../hooks/useMediaQuery'

export function HomePage() {
  const [search, setSearch] = useState('')
  const stats = useAsync(() => collectionApi.stats())
  const cards = useCardsWithPrices()
  // Desktop/tablet keeps the binder grid; phones get the swipeable carousel
  // -- validated at 768px, which reads clearly better as a grid than as a
  // one-card-at-a-time carousel.
  const isDesktop = useMediaQuery('(min-width: 768px)')

  const filteredItems = useMemo(() => {
    if (!cards.items) return []
    const term = search.trim().toLowerCase()
    if (!term) return cards.items
    return cards.items.filter(({ card }) =>
      [card.name, card.collector_number, card.set_name ?? '']
        .join(' ')
        .toLowerCase()
        .includes(term),
    )
  }, [cards.items, search])

  const refreshAll = () => {
    stats.refetch()
    cards.refetch()
  }

  return (
    <PokedexShell>
      <PokedexHeader title="Pokémon Collection" subtitle="Collection mode" />
      <PokedexScreen>
        <div className="flex items-center justify-between">
          <ModeTag led="red">Collection mode</ModeTag>
        </div>

        {stats.loading && <StatsHeaderSkeleton />}
        {stats.error && <ErrorState message={stats.error} onRetry={stats.refetch} />}
        {stats.data && <StatsHeader stats={stats.data} />}

        <Toolbar search={search} onSearchChange={setSearch} onUpdateAllFinished={refreshAll} />

        {cards.loading && (isDesktop ? <CardGridSkeleton /> : <CardCarouselSkeleton />)}
        {cards.error && <ErrorState message={cards.error} onRetry={cards.refetch} />}

        {cards.items && cards.items.length === 0 && (
          <EmptyState
            title="No cards registered"
            description="Agrega tu primera carta Pokémon TCG para empezar a construir tu colección."
            action={
              <Link
                to="/cards/new"
                className="rounded-full bg-price-gold px-4 py-2 text-sm font-semibold text-black transition hover:bg-pokemon-yellow"
              >
                + Agregar primera carta
              </Link>
            }
          />
        )}

        {cards.items && cards.items.length > 0 && filteredItems.length === 0 && (
          <EmptyState title="Sin resultados" description={`No encontramos cartas que coincidan con "${search}".`} />
        )}

        {filteredItems.length > 0 && (isDesktop ? <CardGrid items={filteredItems} /> : <CardCarousel items={filteredItems} />)}
      </PokedexScreen>
    </PokedexShell>
  )
}
