import { useState } from 'react'
import { ApiError, collectionApi } from '../api'
import type { UpdateAllResponse } from '../api'

interface UpdateAllButtonProps {
  onFinished: () => void
}

export function UpdateAllButton({ onFinished }: UpdateAllButtonProps) {
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<UpdateAllResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleClick = async () => {
    setRunning(true)
    setError(null)
    setResult(null)
    try {
      const response = await collectionApi.updateAll()
      setResult(response)
      onFinished()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor.')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="flex flex-col items-start gap-1.5">
      <button
        type="button"
        onClick={handleClick}
        disabled={running}
        className="inline-flex items-center gap-2 rounded-md border border-pokedex-border bg-pokedex-surface-2 px-4 py-2 text-sm font-medium text-pokedex-text transition hover:border-pokedex-red/40 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {running && (
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-pokedex-border border-t-pokedex-red" />
        )}
        {running ? 'Actualizando…' : 'Actualizar precios'}
      </button>

      {running && (
        <p className="font-mono text-[11px] uppercase tracking-wide text-pokedex-muted">Updating market data...</p>
      )}
      {!running && result && (
        <p className="font-mono text-[11px] uppercase tracking-wide text-pokedex-muted">
          Updated: {result.updated} · Failed: {result.failed}
        </p>
      )}
      {!running && error && <p className="text-xs text-pokedex-red">{error}</p>}
    </div>
  )
}
