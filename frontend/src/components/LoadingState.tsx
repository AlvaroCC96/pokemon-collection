interface LoadingStateProps {
  label?: string
}

export function LoadingState({ label = 'Cargando…' }: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-pokedex-muted">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-pokedex-border border-t-pokedex-red" />
      <p className="text-sm">{label}</p>
    </div>
  )
}
