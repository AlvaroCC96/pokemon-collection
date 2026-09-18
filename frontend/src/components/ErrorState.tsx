interface ErrorStateProps {
  message: string
  onRetry?: () => void
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-pokedex-red/30 bg-pokedex-red-dark/10 px-6 py-10 text-center">
      <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-pokedex-red">
        <span className="h-1.5 w-1.5 rounded-full bg-pokedex-red shadow-[0_0_6px_rgba(227,53,53,0.7)]" aria-hidden="true" />
        System error
      </span>
      <p className="text-sm text-pokedex-text/90">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-full border border-pokedex-red/40 px-4 py-1.5 text-sm text-pokedex-text transition hover:bg-pokedex-red/10"
        >
          Reintentar
        </button>
      )}
    </div>
  )
}
