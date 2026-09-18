import { Link } from 'react-router-dom'
import { UpdateAllButton } from './UpdateAllButton'

interface ToolbarProps {
  search: string
  onSearchChange: (value: string) => void
  onUpdateAllFinished: () => void
}

/** Search + primary actions. */
export function Toolbar({ search, onSearchChange, onUpdateAllFinished }: ToolbarProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <div className="relative flex-1">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
          className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-pokedex-muted"
        >
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
          <path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <input
          type="search"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Buscar por nombre, número o set…"
          className="w-full rounded-md border border-pokedex-border bg-pokedex-surface py-2.5 pl-10 pr-4 text-sm text-pokedex-text placeholder:text-pokedex-muted focus:border-pokedex-red/50 focus:outline-none focus:ring-2 focus:ring-pokedex-red/15"
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Link
          to="/cards/new"
          className="inline-flex flex-1 shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-md bg-price-gold px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-pokemon-yellow sm:flex-none"
        >
          + Agregar carta
        </Link>

        <div className="shrink-0">
          <UpdateAllButton onFinished={onUpdateAllFinished} />
        </div>
      </div>
    </div>
  )
}
