import type { CollectionStats } from '../api'
import pikachuSilhouette from '../assets/pokemon/pikachu-silhouette.png'
import { formatDate, formatMoney } from '../utils/format'
import { Led, SectionLabel } from './Pokedex'

// Small line icons for the stat modules -- hand-drawn, no icon library needed
// for four glyphs.
function StackIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
      <path d="m12 3 8 4-8 4-8-4 8-4Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="m4 12 8 4 8-4M4 16l8 4 8-4" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  )
}

function TargetIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
      <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="12" cy="12" r="3.2" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  )
}

function TagIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
      <path
        d="M11.5 4h-6A1.5 1.5 0 0 0 4 5.5v6c0 .4.16.78.44 1.06l8 8a1.5 1.5 0 0 0 2.12 0l6-6a1.5 1.5 0 0 0 0-2.12l-8-8A1.5 1.5 0 0 0 11.5 4Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <circle cx="8.5" cy="8.5" r="1.25" fill="currentColor" />
    </svg>
  )
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
      <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.6" />
      <path d="M12 8v4.5l3 2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

const STAT_ICON = { cards: StackIcon, unique: TargetIcon, priced: TagIcon, pending: ClockIcon } as const

function StatModule({
  icon,
  value,
  label,
}: {
  icon: keyof typeof STAT_ICON
  value: number
  label: string
}) {
  const Icon = STAT_ICON[icon]
  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-pokedex-border bg-pokedex-surface-3/70 px-3 py-2">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-pokedex-bg text-pokedex-red">
        <Icon />
      </span>
      <div className="flex flex-col leading-none">
        <span className="text-base font-semibold text-pokedex-text">{value}</span>
        <span className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.15em] text-pokedex-muted">{label}</span>
      </div>
    </div>
  )
}

export function StatsHeader({ stats }: { stats: CollectionStats }) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-pokedex-border bg-pokedex-surface-2">
      <div className="pokedex-corner" aria-hidden="true" />
      {/* Decorative silhouette -- grayscale + very low opacity, purely
          background texture, never obscures real data. */}
      <img
        src={pikachuSilhouette}
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute -right-6 -top-6 h-48 w-48 select-none opacity-[0.07] grayscale sm:h-56 sm:w-56"
        style={{ filter: 'grayscale(1) brightness(0.3)' }}
      />

      <div className="relative flex flex-col gap-4 px-4 py-4 sm:px-6 sm:py-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          {/* Hero value -- the one thing that must read instantly */}
          <div className="flex flex-col gap-1.5">
            <SectionLabel color="gold">Total collection value</SectionLabel>
            <span className="text-3xl font-bold leading-tight text-price-gold sm:text-4xl">
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

          {stats.last_price_update && (
            <p className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.15em] text-pokedex-muted">
              <Led color="emerald" />
              Updated {formatDate(stats.last_price_update)}
            </p>
          )}
        </div>

        {/* Secondary counts as compact HUD modules -- 2x2 on mobile, row on desktop */}
        <div className="grid grid-cols-2 gap-2 sm:flex sm:items-center sm:gap-3">
          <StatModule icon="cards" value={stats.total_card_count} label="Cards" />
          <StatModule icon="unique" value={stats.distinct_card_count} label="Unique" />
          <StatModule icon="priced" value={stats.cards_with_valuation} label="Priced" />
          <StatModule icon="pending" value={stats.cards_without_valuation} label="Pending" />
        </div>
      </div>
    </div>
  )
}
