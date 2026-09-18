import { ScanlineTopBar } from './Pokedex'

// Reserves the same footprint as StatsHeader so the toolbar/grid below don't
// jump down once stats finish loading.
export function StatsHeaderSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border border-pokedex-border bg-pokedex-surface-2/60">
      <ScanlineTopBar className="opacity-40" />
      <div className="px-4 py-3 sm:px-5 sm:py-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-8">
          <div className="flex flex-col gap-1.5">
            <div className="h-2.5 w-24 animate-pulse rounded bg-pokedex-border/60" />
            <div className="h-8 w-40 animate-pulse rounded bg-pokedex-border/60 sm:h-9 sm:w-48" />
          </div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 sm:flex sm:items-center sm:gap-7 sm:border-l sm:border-pokedex-border sm:pl-7">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="flex flex-col gap-1">
                <div className="h-4 w-8 animate-pulse rounded bg-pokedex-border/60" />
                <div className="h-2.5 w-14 animate-pulse rounded bg-pokedex-border/60" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
