import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, cardsApi } from '../api'
import type { CardCreate, IdentificationCandidate, IdentifyResponse } from '../api'
import { CandidateCard } from '../components/CandidateCard'
import { CharizardDecor } from '../components/CharizardDecor'
import { ErrorState } from '../components/ErrorState'
import { IdentificationPanel } from '../components/IdentificationPanel'
import {
  BackLink,
  ModeTag,
  PokedexHeader,
  PokedexScreen,
  PokedexShell,
  ScanlineTopBar,
  SectionLabel,
} from '../components/Pokedex'
import { LANGUAGE_OPTIONS } from '../utils/languages'

const inputClass =
  'w-full rounded-md border border-pokedex-border bg-pokedex-surface px-3 py-2 text-sm text-pokedex-text placeholder:text-pokedex-muted focus:border-pokedex-red/50 focus:outline-none focus:ring-2 focus:ring-pokedex-red/15'

export function AddCardPage() {
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [collectorNumber, setCollectorNumber] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [language, setLanguage] = useState('')

  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [result, setResult] = useState<IdentifyResponse | null>(null)
  const [selected, setSelected] = useState<IdentificationCandidate | null>(null)
  const [page, setPage] = useState(1)
  const [loadingMore, setLoadingMore] = useState(false)

  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  // Before the first search there is nothing to show next to the form --
  // no placeholder "waiting for a card" panel. Once a search starts (or
  // has a result), the two-column layout takes over.
  const showResultsPanel = searching || result !== null

  const performSearch = async () => {
    if (!name.trim() || !collectorNumber.trim()) return

    setSearching(true)
    setSearchError(null)
    setResult(null)
    setSelected(null)
    setPage(1)

    try {
      const response = await cardsApi.identify({
        name: name.trim(),
        collector_number: collectorNumber.trim(),
        language: language.trim() || undefined,
        page: 1,
      })
      setResult(response)
      if (response.status === 'single_match') {
        setSelected(response.candidates[0])
      }
    } catch (err) {
      setSearchError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor.')
    } finally {
      setSearching(false)
    }
  }

  const handleSearch = (event: FormEvent) => {
    event.preventDefault()
    void performSearch()
  }

  const loadMore = async () => {
    if (!result?.has_more) return
    const nextPage = page + 1
    setLoadingMore(true)
    setSearchError(null)

    try {
      const response = await cardsApi.identify({
        name: name.trim(),
        collector_number: collectorNumber.trim(),
        language: language.trim() || undefined,
        page: nextPage,
      })
      setResult((prev) =>
        prev
          ? {
              ...prev,
              status: 'multiple_matches',
              candidates: [...prev.candidates, ...response.candidates],
              has_more: response.has_more,
            }
          : response,
      )
      setPage(nextPage)
    } catch (err) {
      setSearchError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor.')
    } finally {
      setLoadingMore(false)
    }
  }

  const createCard = async (candidate: IdentificationCandidate | null) => {
    setCreating(true)
    setCreateError(null)

    const payload: CardCreate = {
      name: candidate?.name ?? name.trim(),
      collector_number: candidate?.collector_number ?? collectorNumber.trim(),
      quantity,
      language: language.trim() || null,
      set_name: candidate?.set_name ?? null,
      rarity: candidate?.rarity ?? null,
      image_url: candidate?.image_url ?? null,
    }

    try {
      const card = await cardsApi.create(payload)
      navigate(`/cards/${card.id}`)
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.message : 'No se pudo guardar la carta.')
      setCreating(false)
    }
  }

  return (
    <PokedexShell>
      <PokedexHeader title="Pokémon Collection" subtitle="Scan mode" />
      <PokedexScreen>
        {/* HUD labels pinned to the panel's own corner, independent of the
            content padding below -- PokedexScreen is `relative` for this. */}
        <div className="absolute right-3 top-3 sm:right-4 sm:top-4">
          <ModeTag led="red">Scan mode</ModeTag>
        </div>
        {!showResultsPanel && (
          <p className="pointer-events-none absolute bottom-4 left-4 hidden select-none font-mono text-[9px] uppercase leading-relaxed tracking-[0.3em] text-pokedex-muted/40 md:block">
            Gotta
            <br />
            Catch
            <br />
            &apos;Em All
          </p>
        )}

        <div className="relative isolate mx-auto flex w-full max-w-5xl flex-col gap-6 overflow-hidden">
        {/* Background layer, not a section -- only while the form has the
            screen to itself (no results yet). `isolate` above gives this
            wrapper its own stacking context so CharizardDecor's negative
            z-index stays scoped here (above this wrapper's own transparent
            background, i.e. PokedexScreen's graphite panel behind it) and
            below every real, normal-flow child -- without `isolate`, a
            `position:relative` element with no z-index of its own does NOT
            create a stacking context, so the negative z-index escapes all
            the way up and renders behind PokedexScreen's opaque background
            instead, which is why it was invisible. */}
        {!showResultsPanel && <CharizardDecor />}
        <BackLink />

        <div
          className={
            showResultsPanel
              ? 'grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,380px)_1fr] lg:items-stretch'
              : 'mx-auto w-full max-w-md'
          }
        >
          <form
            onSubmit={handleSearch}
            className="relative flex flex-col overflow-hidden rounded-lg border border-pokedex-border bg-pokedex-surface-2"
          >
            <ScanlineTopBar />
            <div className="flex flex-col gap-4 p-5 sm:p-6">
              <SectionLabel>Search data</SectionLabel>

              <div className="grid grid-cols-1 gap-4">
                <label className="flex flex-col gap-1.5 text-sm text-pokedex-text/80">
                  Nombre
                  <input
                    className={inputClass}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Charizard ex"
                    required
                  />
                </label>

                <label className="flex flex-col gap-1.5 text-sm text-pokedex-text/80">
                  Número de coleccionista
                  <input
                    className={inputClass}
                    value={collectorNumber}
                    onChange={(e) => setCollectorNumber(e.target.value)}
                    placeholder="199/165"
                    required
                  />
                </label>

                <label className="flex flex-col gap-1.5 text-sm text-pokedex-text/80">
                  Idioma <span className="text-pokedex-muted">(opcional)</span>
                  <select className={inputClass} value={language} onChange={(e) => setLanguage(e.target.value)}>
                    {LANGUAGE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="flex flex-col gap-1.5 text-sm text-pokedex-text/80">
                  Cantidad
                  <input
                    type="number"
                    min={1}
                    className={inputClass}
                    value={quantity}
                    onChange={(e) => setQuantity(Math.max(1, Number(e.target.value) || 1))}
                  />
                </label>
              </div>

              <button
                type="submit"
                disabled={searching || !name.trim() || !collectorNumber.trim()}
                className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-pokedex-red px-5 py-2.5 text-sm font-semibold uppercase tracking-wide text-white transition hover:bg-pokedex-red/85 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {searching && (
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                )}
                {searching ? 'Scanning…' : 'Scan'}
              </button>
            </div>
          </form>

          {showResultsPanel && (
            <IdentificationPanel
              searching={searching}
              result={result}
              selected={selected}
              creating={creating}
              onCreate={createCard}
            />
          )}
        </div>

        {searchError && <ErrorState message={searchError} onRetry={performSearch} />}

        {result && result.status === 'multiple_matches' && (
          <section className="flex flex-col gap-4 rounded-lg border border-pokedex-border bg-pokedex-surface-2 p-5">
            <div className="flex items-center justify-between">
              <SectionLabel color="gold">Matches</SectionLabel>
              <span className="rounded-md bg-pokedex-bg px-2.5 py-0.5 font-mono text-xs font-medium text-pokedex-text/80">
                {result.candidates.length}
                {result.has_more ? '+' : ''}
              </span>
            </div>

            <div className="grid grid-cols-[repeat(auto-fill,minmax(130px,1fr))] gap-3 sm:grid-cols-[repeat(auto-fill,minmax(150px,1fr))] sm:gap-4">
              {result.candidates.map((candidate, index) => (
                <CandidateCard
                  key={`${candidate.external_id}-${index}`}
                  candidate={candidate}
                  selected={selected?.external_id === candidate.external_id}
                  onSelect={() => setSelected(candidate)}
                />
              ))}
            </div>

            {result.has_more && (
              <button
                type="button"
                onClick={() => void loadMore()}
                disabled={loadingMore}
                className="inline-flex w-fit items-center gap-2 self-center rounded-md border border-pokedex-border px-4 py-1.5 text-sm text-pokedex-text/80 transition hover:bg-pokedex-surface disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loadingMore && (
                  <span className="h-3 w-3 animate-spin rounded-full border-2 border-pokedex-border border-t-pokedex-text" />
                )}
                {loadingMore ? 'Cargando…' : 'Cargar más'}
              </button>
            )}

            <button
              type="button"
              onClick={() => createCard(null)}
              disabled={creating}
              className="w-fit self-start text-xs text-pokedex-muted underline decoration-dotted hover:text-pokedex-text disabled:opacity-60"
            >
              Ninguna de estas, guardar manualmente
            </button>
          </section>
        )}

        {createError && <ErrorState message={createError} />}
        </div>
      </PokedexScreen>
    </PokedexShell>
  )
}
