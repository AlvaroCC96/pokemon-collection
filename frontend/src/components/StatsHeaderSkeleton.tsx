// Reserves the same footprint as StatsHeader so the toolbar/grid below don't
// jump down once stats finish loading.
export function StatsHeaderSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border border-pokedex-border bg-pokedex-surface-2">
      <div className="flex flex-col gap-4 px-4 py-4 sm:px-6 sm:py-5">
        <div className="flex flex-col gap-1.5">
          <div className="h-2.5 w-32 animate-pulse rounded bg-pokedex-border/60" />
          <div className="h-9 w-48 animate-pulse rounded bg-pokedex-border/60 sm:h-10 sm:w-56" />
        </div>
        <div className="grid grid-cols-2 gap-2 sm:flex sm:items-center sm:gap-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-12 flex-1 animate-pulse rounded-lg bg-pokedex-surface-3/70 sm:w-28" />
          ))}
        </div>
      </div>
    </div>
  )
}
