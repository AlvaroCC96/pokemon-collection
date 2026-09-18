import type { ReactNode } from 'react'
import type { IdentificationCandidate, IdentifyResponse } from '../api'
import { CardImage } from './CardImage'
import { Led, ScanlineTopBar, SectionLabel } from './Pokedex'

interface IdentificationPanelProps {
  searching: boolean
  result: IdentifyResponse | null
  selected: IdentificationCandidate | null
  creating: boolean
  onCreate: (candidate: IdentificationCandidate | null) => void
}

function PanelShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex h-full flex-col overflow-hidden rounded-lg border border-pokedex-border bg-pokedex-surface-2">
      <ScanlineTopBar />
      <div className="flex flex-1 flex-col gap-4 p-5 sm:p-6">{children}</div>
    </div>
  )
}

function StatusChip({ label, led }: { label: string; led: 'red' | 'yellow' | 'gold' | 'emerald' | 'muted' }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-pokedex-border bg-pokedex-bg px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-pokedex-muted">
      <Led color={led} />
      {label}
    </span>
  )
}

function PanelHeading({ status, led }: { status: string; led: 'red' | 'yellow' | 'gold' | 'emerald' | 'muted' }) {
  return (
    <div className="flex items-center justify-between">
      <SectionLabel>Target</SectionLabel>
      <StatusChip label={status} led={led} />
    </div>
  )
}

function CandidatePreview({
  candidate,
  creating,
  onCreate,
  showDiscard,
}: {
  candidate: IdentificationCandidate
  creating: boolean
  onCreate: (candidate: IdentificationCandidate | null) => void
  showDiscard: boolean
}) {
  const metaRows = [
    candidate.collector_number && { label: 'Número', value: candidate.collector_number },
    candidate.set_name && { label: 'Set', value: candidate.set_name },
    candidate.rarity && { label: 'Rareza', value: candidate.rarity },
    candidate.language && { label: 'Idioma', value: candidate.language },
    candidate.source && { label: 'Fuente', value: candidate.source },
  ].filter((row): row is { label: string; value: string } => Boolean(row))

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
      <div className="aspect-[3/4] w-full max-w-[200px] shrink-0 self-center sm:self-start">
        <CardImage src={candidate.image_url} alt={candidate.name} className="h-full w-full" />
      </div>
      <div className="flex flex-1 flex-col gap-3">
        <h3 className="text-lg font-semibold text-pokedex-text">{candidate.name}</h3>
        {metaRows.length > 0 && (
          <dl className="flex flex-col gap-1 text-sm">
            {metaRows.map((row) => (
              <div key={row.label} className="flex gap-2">
                <dt className="w-16 shrink-0 text-pokedex-muted">{row.label}</dt>
                <dd className="text-pokedex-text/90">{row.value}</dd>
              </div>
            ))}
          </dl>
        )}
        <div className="mt-1 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onCreate(candidate)}
            disabled={creating}
            className="rounded-md bg-price-gold px-4 py-2 text-sm font-semibold text-black transition hover:bg-pokemon-yellow disabled:cursor-not-allowed disabled:opacity-60"
          >
            {creating ? 'Agregando…' : 'Agregar a mi colección'}
          </button>
          {showDiscard && (
            <button
              type="button"
              onClick={() => onCreate(null)}
              disabled={creating}
              className="rounded-md border border-pokedex-border px-4 py-2 text-sm text-pokedex-text/80 transition hover:bg-pokedex-surface disabled:opacity-60"
            >
              No es esta, guardar manualmente
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export function IdentificationPanel({ searching, result, selected, creating, onCreate }: IdentificationPanelProps) {
  if (searching) {
    return (
      <PanelShell>
        <PanelHeading status="Searching" led="gold" />
        <div className="flex flex-1 flex-col items-center justify-center gap-3 py-6 text-center">
          <span className="h-8 w-8 animate-spin rounded-full border-2 border-pokedex-border border-t-pokedex-red" />
          <p className="text-sm text-pokedex-muted">Buscando en el catálogo…</p>
        </div>
      </PanelShell>
    )
  }

  // Nothing searched yet: the form panel alone carries the screen, no
  // placeholder "waiting for a card" panel next to it.
  if (!result) return null

  if (result.status === 'not_found') {
    return (
      <PanelShell>
        <PanelHeading status="Not found" led="red" />
        <div className="flex flex-1 flex-col items-center justify-center gap-3 py-4 text-center">
          <p className="text-sm text-pokedex-text/90">No encontramos esta carta en el catálogo.</p>
          <p className="max-w-[240px] text-xs text-pokedex-muted">Puedes guardarla igual con los datos que ingresaste.</p>
          <button
            type="button"
            onClick={() => onCreate(null)}
            disabled={creating}
            className="mt-1 rounded-md border border-pokedex-border bg-pokedex-surface px-4 py-2 text-sm font-medium text-pokedex-text transition hover:border-pokedex-red/40 disabled:opacity-60"
          >
            {creating ? 'Guardando…' : 'Guardar de todas formas'}
          </button>
        </div>
      </PanelShell>
    )
  }

  if (result.status === 'single_match') {
    const candidate = selected ?? result.candidates[0]
    return (
      <PanelShell>
        <PanelHeading status="Match found" led="emerald" />
        <CandidatePreview candidate={candidate} creating={creating} onCreate={onCreate} showDiscard />
      </PanelShell>
    )
  }

  // multiple_matches
  if (selected) {
    return (
      <PanelShell>
        <PanelHeading status="Match found" led="emerald" />
        <CandidatePreview candidate={selected} creating={creating} onCreate={onCreate} showDiscard />
      </PanelShell>
    )
  }

  return (
    <PanelShell>
      <PanelHeading status="Multiple matches" led="gold" />
      <div className="flex flex-1 flex-col items-center justify-center gap-2 py-4 text-center">
        <p className="text-sm text-pokedex-text/90">
          Encontramos <span className="font-semibold text-pokedex-text">{result.candidates.length}</span> coincidencias
          {result.has_more ? ' o más' : ''}.
        </p>
        <p className="max-w-[240px] text-xs text-pokedex-muted">Elige la carta correcta en los resultados de abajo.</p>
      </div>
    </PanelShell>
  )
}
