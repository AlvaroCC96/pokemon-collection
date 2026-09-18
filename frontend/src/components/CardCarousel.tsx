import useEmblaCarousel from 'embla-carousel-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import type { CardWithLatestPrice } from '../hooks/useCardsWithPrices'
import { formatMoney } from '../utils/format'
import { CardImage } from './CardImage'
import { PercentBadge } from './PercentBadge'

const DOTS_THRESHOLD = 12

/** Mobile collection view -- one big card at a time, swipe to move through
 * the binder instead of a cramped grid. Desktop keeps CardGrid; this is
 * Embla Carousel (embla-carousel-react), chosen over alternatives because
 * it ships a tiny, dependency-free core built specifically for touch
 * swipe, has first-class React bindings/TS types, and needs no extra
 * plugin for this use case (no autoplay, no fade, just drag-to-scroll). */
export function CardCarousel({ items }: { items: CardWithLatestPrice[] }) {
  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: false, align: 'center', containScroll: 'trimSnaps' })
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [canScrollPrev, setCanScrollPrev] = useState(false)
  const [canScrollNext, setCanScrollNext] = useState(false)
  const prevIdsKey = useRef<string>('')

  const onSelect = useCallback(() => {
    if (!emblaApi) return
    setSelectedIndex(emblaApi.selectedScrollSnap())
    setCanScrollPrev(emblaApi.canScrollPrev())
    setCanScrollNext(emblaApi.canScrollNext())
  }, [emblaApi])

  useEffect(() => {
    if (!emblaApi) return
    onSelect()
    emblaApi.on('select', onSelect)
    emblaApi.on('reInit', onSelect)
    return () => {
      emblaApi.off('select', onSelect)
      emblaApi.off('reInit', onSelect)
    }
  }, [emblaApi, onSelect])

  // Re-measure whenever the slide count changes (e.g. a search filters the
  // collection down), and only jump if the current position is no longer
  // valid -- a same-length refresh (price update) shouldn't reset the user
  // back to card 1.
  const idsKey = items.map((item) => item.card.id).join(',')
  useEffect(() => {
    if (!emblaApi) return
    emblaApi.reInit()
    if (idsKey !== prevIdsKey.current) {
      prevIdsKey.current = idsKey
      const maxIndex = Math.max(items.length - 1, 0)
      if (emblaApi.selectedScrollSnap() > maxIndex) {
        emblaApi.scrollTo(maxIndex, true)
      }
    }
  }, [emblaApi, idsKey, items.length])

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'ArrowLeft') emblaApi?.scrollPrev()
    if (event.key === 'ArrowRight') emblaApi?.scrollNext()
  }

  if (items.length === 0) return null

  const active = items[Math.min(selectedIndex, items.length - 1)]
  const showDots = items.length <= DOTS_THRESHOLD

  return (
    <div className="flex flex-col gap-3">
      <div
        ref={emblaRef}
        className="overflow-hidden"
        role="group"
        aria-roledescription="carousel"
        aria-label="Colección de cartas"
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        {/* will-change hints the browser to promote this to its own GPU
            layer ahead of time, so Embla's translate3d during a swipe moves
            an already-rasterized layer instead of re-rasterizing the large
            card images on every frame -- that live resampling is what reads
            as a quick pixelated flicker mid-swipe. */}
        <div className="-ml-3 flex touch-pan-y will-change-transform">
          {items.map(({ card, latestSnapshot }) => (
            <div key={card.id} className="min-w-0 shrink-0 grow-0 basis-[86%] pl-3">
              <Link
                to={`/cards/${card.id}`}
                className="relative flex flex-col gap-3 rounded-lg border border-transparent p-3 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pokedex-red/50"
              >
                <div className="relative aspect-[3/4] w-full">
                  <CardImage src={card.image_url} alt={card.name} className="h-full w-full" />
                  {/* No backdrop-blur here -- it forces a repaint every
                      frame while Embla transforms the track during a
                      swipe, which read as flicker on some mobile GPUs. */}
                  <span className="absolute right-2 top-2 rounded-md border border-pokedex-red/30 bg-black/80 px-2 py-0.5 font-mono text-xs font-medium text-pokedex-text">
                    x{card.quantity}
                  </span>
                </div>
                <div className="flex flex-col gap-1">
                  <h3 className="line-clamp-2 text-base font-semibold leading-snug text-pokedex-text">{card.name}</h3>
                  <p className="truncate text-xs text-pokedex-muted">
                    {card.collector_number}
                    {card.set_name ? ` · ${card.set_name}` : ''}
                  </p>
                  {latestSnapshot ? (
                    <div className="mt-1 flex items-center gap-2">
                      <span className="text-lg font-bold text-price-gold">
                        {formatMoney(latestSnapshot.estimated_price, latestSnapshot.currency)}
                      </span>
                      <PercentBadge value={latestSnapshot.price_change_percent} />
                    </div>
                  ) : (
                    <span className="mt-1 w-fit rounded-md border border-dashed border-price-gold/25 px-2 py-0.5 text-xs text-price-gold/60">
                      Sin valoración
                    </span>
                  )}
                </div>
              </Link>
            </div>
          ))}
        </div>
      </div>

      <span className="sr-only" aria-live="polite">
        Carta {selectedIndex + 1} de {items.length}: {active.card.name}
      </span>

      <div className="flex items-center justify-center gap-4">
        <button
          type="button"
          onClick={() => emblaApi?.scrollPrev()}
          disabled={!canScrollPrev}
          aria-label="Carta anterior"
          className="flex h-9 w-9 items-center justify-center rounded-full border border-pokedex-border bg-pokedex-surface-2 text-pokedex-text transition hover:border-pokedex-red/40 disabled:opacity-30"
        >
          ‹
        </button>

        {showDots ? (
          <div className="flex items-center gap-1.5">
            {items.map((item, index) => (
              <span
                key={item.card.id}
                aria-hidden="true"
                className={`h-1.5 w-1.5 rounded-full transition ${
                  index === selectedIndex ? 'bg-pokedex-red' : 'bg-pokedex-border'
                }`}
              />
            ))}
          </div>
        ) : (
          <span className="min-w-[64px] text-center font-mono text-sm text-pokedex-muted">
            <span className="font-semibold text-pokedex-text">{selectedIndex + 1}</span> / {items.length}
          </span>
        )}

        <button
          type="button"
          onClick={() => emblaApi?.scrollNext()}
          disabled={!canScrollNext}
          aria-label="Carta siguiente"
          className="flex h-9 w-9 items-center justify-center rounded-full border border-pokedex-border bg-pokedex-surface-2 text-pokedex-text transition hover:border-pokedex-red/40 disabled:opacity-30"
        >
          ›
        </button>
      </div>
    </div>
  )
}
