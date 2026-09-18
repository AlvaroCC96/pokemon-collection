import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError, cardsApi } from '../api'
import { ConfidenceBadge, MarketScopeBadge } from '../components/Badges'
import { CardImage } from '../components/CardImage'
import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { PercentBadge } from '../components/PercentBadge'
import { Led, ModeTag, PokedexHeader, PokedexScreen, PokedexShell, ScanlineTopBar, SectionLabel } from '../components/Pokedex'
import { PriceChart } from '../components/PriceChart'
import { useAsync } from '../hooks/useAsync'
import { formatDate, formatMoney } from '../utils/format'

export function CardDetailPage() {
  const params = useParams<{ id: string }>()
  const cardId = Number(params.id)
  const navigate = useNavigate()

  const card = useAsync(() => cardsApi.get(cardId), [cardId])
  const history = useAsync(() => cardsApi.priceHistory(cardId), [cardId])

  const [updating, setUpdating] = useState(false)
  const [updateError, setUpdateError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  const snapshots = history.data?.snapshots ?? []
  const latest = snapshots.at(-1) ?? null

  const handleUpdatePrice = async () => {
    setUpdating(true)
    setUpdateError(null)
    try {
      await cardsApi.updatePrice(cardId)
      history.refetch()
    } catch (err) {
      setUpdateError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor.')
    } finally {
      setUpdating(false)
    }
  }

  const handleDelete = async () => {
    if (!window.confirm('¿Eliminar esta carta de tu colección? Esta acción no se puede deshacer.')) return
    setDeleting(true)
    try {
      await cardsApi.remove(cardId)
      navigate('/')
    } catch (err) {
      setDeleting(false)
      window.alert(err instanceof ApiError ? err.message : 'No se pudo eliminar la carta.')
    }
  }

  if (card.loading) {
    return (
      <PokedexShell>
        <PokedexHeader title="Pokémon Collection" subtitle="Card data" />
        <PokedexScreen>
          <LoadingState label="Cargando carta…" />
        </PokedexScreen>
      </PokedexShell>
    )
  }

  if (card.error) {
    return (
      <PokedexShell>
        <PokedexHeader title="Pokémon Collection" subtitle="Card data" />
        <PokedexScreen>
          <ErrorState message={card.error} onRetry={card.refetch} />
        </PokedexScreen>
      </PokedexShell>
    )
  }

  if (!card.data) return null

  const c = card.data

  return (
    <PokedexShell>
      <PokedexHeader title="Pokémon Collection" subtitle="Card data" />
      <PokedexScreen>
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
          <div className="flex items-center justify-between">
            <Link to="/" className="text-sm text-pokedex-muted hover:text-pokedex-text">
              ← Volver a mi colección
            </Link>
            <ModeTag led="red">Card data</ModeTag>
          </div>

          {/* Single column through tablet widths (768px included) -- only a
              real desktop viewport gets the side-by-side layout, per the
              "don't compress the desktop layout into the phone" requirement. */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,340px)_1fr] lg:gap-8">
            <div className="mx-auto aspect-[3/4] w-full max-w-[340px] overflow-hidden rounded-2xl border border-pokedex-border bg-pokedex-bg lg:mx-0">
              <CardImage src={c.image_url} alt={c.name} className="h-full w-full" />
            </div>

            <div className="flex flex-col gap-4">
              <div>
                <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.15em] text-pokedex-muted">
                  <Led color={c.identified ? 'emerald' : 'muted'} />
                  {c.identified ? 'Identified' : 'Unverified'}
                </div>
                <h1 className="mt-1 text-2xl font-bold tracking-tight text-pokedex-text">{c.name}</h1>
                <p className="text-sm text-pokedex-muted">
                  {c.collector_number}
                  {c.set_name ? ` · ${c.set_name}` : ''}
                </p>
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-pokedex-muted">
                  {c.rarity && <span className="rounded-full border border-pokedex-border px-2.5 py-0.5">{c.rarity}</span>}
                  {c.language && (
                    <span className="rounded-full border border-pokedex-border px-2.5 py-0.5">{c.language}</span>
                  )}
                  <span className="rounded-full border border-pokedex-border px-2.5 py-0.5">Cantidad: {c.quantity}</span>
                </div>
              </div>

              <div className="overflow-hidden rounded-2xl border border-pokedex-border bg-pokedex-surface-2/60">
                <ScanlineTopBar />
                <div className="p-4">
                  <SectionLabel color="gold">Value</SectionLabel>
                  <div className="mt-2">
                    {latest ? (
                      <>
                        <div className="flex flex-wrap items-baseline gap-2">
                          <span className="text-3xl font-bold text-price-gold">
                            {formatMoney(latest.estimated_price, latest.currency)}
                          </span>
                          <PercentBadge value={latest.price_change_percent} />
                        </div>
                        {(latest.low_price !== null || latest.high_price !== null) && (
                          <p className="mt-1 text-sm text-pokedex-muted">
                            Rango: {latest.low_price !== null ? formatMoney(latest.low_price, latest.currency) : '—'} –{' '}
                            {latest.high_price !== null ? formatMoney(latest.high_price, latest.currency) : '—'}
                          </p>
                        )}
                        <div className="mt-3 flex flex-wrap gap-2">
                          <MarketScopeBadge scope={latest.market_scope} />
                          <ConfidenceBadge label={latest.confidence_label} />
                        </div>
                        <p className="mt-3 text-xs text-pokedex-muted/70">
                          Última actualización: {formatDate(latest.checked_at)} · {latest.source_count} fuente
                          {latest.source_count === 1 ? '' : 's'} usada{latest.source_count === 1 ? '' : 's'}
                        </p>
                      </>
                    ) : (
                      <p className="text-sm text-pokedex-muted">Sin valoración todavía.</p>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={handleUpdatePrice}
                    disabled={updating}
                    className="mt-4 inline-flex items-center gap-2 rounded-full border border-pokedex-border bg-pokedex-surface px-4 py-2 text-sm font-medium text-pokedex-text transition hover:border-pokedex-red/40 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {updating && (
                      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-pokedex-border border-t-pokedex-red" />
                    )}
                    {updating ? 'Buscando precio…' : 'Actualizar precio'}
                  </button>
                  {updating && <p className="mt-1.5 text-xs text-pokedex-muted">Esto puede tardar hasta un minuto.</p>}
                  {updateError && <p className="mt-1.5 text-xs text-pokedex-red">{updateError}</p>}
                </div>
              </div>
            </div>
          </div>

          <section className="rounded-2xl border border-pokedex-border bg-pokedex-surface-2/60 p-4">
            <div className="mb-3">
              <SectionLabel color="gold">Historical data</SectionLabel>
            </div>
            {history.loading && <LoadingState label="Cargando histórico…" />}
            {history.error && <ErrorState message={history.error} onRetry={history.refetch} />}
            {history.data && snapshots.length === 0 && (
              <p className="text-sm text-pokedex-muted">Todavía no hay histórico — usa "Actualizar precio" para generarlo.</p>
            )}
            {snapshots.length > 0 && <PriceChart snapshots={snapshots} />}
          </section>

          {latest && latest.observations.length > 0 && (
            <section className="rounded-2xl border border-pokedex-border bg-pokedex-surface-2/60 p-4">
              <div className="mb-3">
                <SectionLabel>Sources</SectionLabel>
              </div>
              <ul className="flex flex-col divide-y divide-pokedex-border">
                {latest.observations.map((source, index) => (
                  <li key={index} className="flex flex-col gap-0.5 py-2.5 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-medium text-pokedex-text/90">{source.source_name}</span>
                      <span className={source.included_in_estimate ? 'text-pokedex-text' : 'text-pokedex-muted line-through'}>
                        {formatMoney(source.observed_price, source.currency)}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs text-pokedex-muted">
                      <span>{source.market_region === 'CHILE' ? 'Chile' : 'Internacional'}</span>
                      {source.language && <span>· {source.language}</span>}
                      {source.is_outlier && <span className="text-rose-400">· valor atípico, excluido</span>}
                      {!source.is_outlier && !source.included_in_estimate && (
                        <span>· no usado en la estimación</span>
                      )}
                      {source.source_url && (
                        <a
                          href={source.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-sky-400 hover:underline"
                        >
                          Ver fuente
                        </a>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className="self-start text-xs text-pokedex-muted underline decoration-dotted hover:text-pokedex-red disabled:opacity-60"
          >
            Eliminar carta de mi colección
          </button>
        </div>
      </PokedexScreen>
    </PokedexShell>
  )
}
