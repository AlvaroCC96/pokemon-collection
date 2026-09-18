import { Link } from 'react-router-dom'
import type { CardWithLatestPrice } from '../hooks/useCardsWithPrices'
import { formatMoney } from '../utils/format'
import { CardImage } from './CardImage'
import { PercentBadge } from './PercentBadge'

export function CardTile({ card, latestSnapshot }: CardWithLatestPrice) {
  return (
    <Link
      to={`/cards/${card.id}`}
      className="group relative flex flex-col overflow-hidden rounded-lg border border-transparent transition hover:-translate-y-0.5 hover:border-pokedex-red/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pokedex-red/50"
    >
      <div className="relative aspect-[3/4] w-full">
        <CardImage
          src={card.image_url}
          alt={card.name}
          className="h-full w-full transition duration-300 group-hover:scale-[1.03]"
        />
        <span className="absolute right-2 top-2 rounded-md border border-pokedex-red/30 bg-black/70 px-2 py-0.5 font-mono text-xs font-medium text-pokedex-text backdrop-blur">
          x{card.quantity}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-1 p-2.5 sm:p-3">
        <h3 className="line-clamp-2 text-sm font-semibold leading-snug text-pokedex-text">{card.name}</h3>
        <p className="truncate text-xs text-pokedex-muted">
          {card.collector_number}
          {card.set_name ? ` · ${card.set_name}` : ''}
        </p>

        <div className="mt-auto flex items-end justify-between gap-2 pt-2">
          {latestSnapshot ? (
            <div className="flex flex-col">
              <span className="text-sm font-semibold text-price-gold">
                {formatMoney(latestSnapshot.estimated_price, latestSnapshot.currency)}
              </span>
              <PercentBadge value={latestSnapshot.price_change_percent} className="text-xs" />
            </div>
          ) : (
            <span className="rounded-md border border-dashed border-price-gold/25 px-2 py-0.5 text-xs text-price-gold/60">
              Sin valoración
            </span>
          )}
        </div>
      </div>
    </Link>
  )
}
