import type { ReactNode } from 'react'

interface EmptyStateProps {
  title: string
  description?: string
  action?: ReactNode
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed border-pokedex-border bg-pokedex-surface-2/60 px-6 py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-pokedex-surface-3 text-price-gold">
        <svg viewBox="0 0 24 24" fill="none" className="h-8 w-8" aria-hidden="true">
          <path
            d="M12 3v6m0 0-3-3m3 3 3-3M5 13h14l-1.5 7h-11L5 13Z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <div className="space-y-1">
        <h2 className="text-lg font-semibold text-pokedex-text">{title}</h2>
        {description && <p className="max-w-sm text-sm text-pokedex-muted">{description}</p>}
      </div>
      {action}
    </div>
  )
}
