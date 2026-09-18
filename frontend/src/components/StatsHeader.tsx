import type { CollectionStats } from '../api'
import { formatDate, formatMoney } from '../utils/format'
import { Led, ScanlineTopBar, SectionLabel } from './Pokedex'

function CompactStat({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex items-baseline gap-1.5 sm:flex-col sm:items-start sm:gap-0.5">
      <span className="text-base font-semibold text-pokedex-text sm:text-lg">{value}</span>
      <span className="text-[10px] uppercase tracking-wide text-pokedex-muted">{label}</span>
    </div>
  )
}

export function StatsHeader({ stats }: { stats: CollectionStats }) {
  return (
    <div className="overflow-hidden rounded-xl border border-pokedex-border bg-pokedex-surface-2/60">
      <ScanlineTopBar />
      <div className="px-4 py-3 sm:px-5 sm:py-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-8">
          {/* Hero value -- the one thing that must read instantly */}
          <div className="flex flex-col gap-1">
            <SectionLabel color="gold">Collection value</SectionLabel>
            <span className="text-2xl font-bold leading-tight text-price-gold sm:text-3xl">
              {formatMoney(stats.total_estimated_value, stats.currency)}
            </span>
            {stats.other_currency_totals.length > 0 && (
              <span className="text-[11px] text-pokedex-muted">
                +{' '}
                {stats.other_currency_totals
                  .map((t) => `${formatMoney(t.total_value, t.currency)} (${t.card_count})`)
                  .join(', ')}{' '}
                en otra moneda, no incluido
              </span>
            )}
          </div>

          {/* Secondary counts -- compact 2x2 on mobile, inline segmented row on desktop */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 sm:flex sm:items-center sm:gap-7 sm:border-l sm:border-pokedex-border sm:pl-7">
            <CompactStat value={stats.total_card_count} label="cards" />
            <CompactStat value={stats.distinct_card_count} label="unique" />
            <CompactStat value={stats.cards_with_valuation} label="priced" />
            <CompactStat value={stats.cards_without_valuation} label="pending" />
          </div>
        </div>

        {stats.last_price_update && (
          <p className="mt-2.5 flex items-center gap-1.5 text-[11px] text-pokedex-muted/70 sm:mt-3">
            <Led color="emerald" />
            Actualizado {formatDate(stats.last_price_update)}
          </p>
        )}
      </div>
    </div>
  )
}
