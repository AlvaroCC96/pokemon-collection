import type { IdentificationCandidate } from '../api'
import { CardImage } from './CardImage'

interface CandidateCardProps {
  candidate: IdentificationCandidate
  selected?: boolean
  onSelect: () => void
}

export function CandidateCard({ candidate, selected = false, onSelect }: CandidateCardProps) {
  // Some sources (e.g. Japan's official search) don't expose a collector
  // number or set at all -- never invented, so skip the line entirely
  // instead of showing an empty " · " when both are missing.
  const metaParts = [candidate.collector_number, candidate.set_name].filter(Boolean)

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`flex flex-col overflow-hidden rounded-2xl border bg-pokedex-surface-2/60 text-left transition ${
        selected ? 'border-pokedex-red ring-2 ring-pokedex-red/40' : 'border-pokedex-border hover:border-pokedex-red/30'
      }`}
    >
      <div className="aspect-[3/4] w-full bg-pokedex-bg">
        <CardImage src={candidate.image_url} alt={candidate.name} className="h-full w-full" />
      </div>
      <div className="flex flex-col gap-0.5 p-2.5">
        <span className="truncate text-sm font-medium text-pokedex-text">{candidate.name}</span>
        {metaParts.length > 0 && (
          <span className="truncate text-xs text-pokedex-muted">{metaParts.join(' · ')}</span>
        )}
        {candidate.rarity && <span className="truncate text-xs text-pokedex-muted/70">{candidate.rarity}</span>}
      </div>
    </button>
  )
}
