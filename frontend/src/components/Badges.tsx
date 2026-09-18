import type { ConfidenceLabel, MarketScope } from '../api'

const CONFIDENCE_STYLES: Record<ConfidenceLabel, string> = {
  HIGH: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  MEDIUM: 'bg-price-gold/10 text-price-gold border-price-gold/30',
  LOW: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
}

const CONFIDENCE_LABELS: Record<ConfidenceLabel, string> = {
  HIGH: 'Confianza alta',
  MEDIUM: 'Confianza media',
  LOW: 'Confianza baja',
}

export function ConfidenceBadge({ label }: { label: ConfidenceLabel }) {
  return (
    <span className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${CONFIDENCE_STYLES[label]}`}>
      {CONFIDENCE_LABELS[label]}
    </span>
  )
}

const SCOPE_LABELS: Record<MarketScope, string> = {
  CHILE: 'Mercado: Chile',
  INTERNATIONAL: 'Mercado: Internacional',
}

export function MarketScopeBadge({ scope }: { scope: MarketScope }) {
  const isChile = scope === 'CHILE'
  return (
    <span
      className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${
        isChile
          ? 'border-price-gold/30 bg-price-gold/10 text-price-gold'
          : 'border-pokedex-border bg-pokedex-surface-2 text-pokedex-muted'
      }`}
    >
      {SCOPE_LABELS[scope]}
    </span>
  )
}
