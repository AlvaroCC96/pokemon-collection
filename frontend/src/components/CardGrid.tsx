import type { CardWithLatestPrice } from '../hooks/useCardsWithPrices'
import { CardTile } from './CardTile'

// auto-fill instead of fixed breakpoints: the grid keeps filling extra width
// with more columns (binder-like) on any monitor size, ultrawide included,
// without ever growing a column past its natural card proportions.
export function CardGrid({ items }: { items: CardWithLatestPrice[] }) {
  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(140px,1fr))] gap-3 sm:grid-cols-[repeat(auto-fill,minmax(170px,1fr))] sm:gap-4">
      {items.map((item) => (
        <CardTile key={item.card.id} card={item.card} latestSnapshot={item.latestSnapshot} />
      ))}
    </div>
  )
}
