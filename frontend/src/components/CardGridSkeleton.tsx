// Mirrors CardGrid's column layout and CardTile's aspect ratio so the
// collection never jumps around once the real data/images arrive.
export function CardGridSkeleton({ count = 12 }: { count?: number }) {
  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(140px,1fr))] gap-3 sm:grid-cols-[repeat(auto-fill,minmax(170px,1fr))] sm:gap-4">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="flex flex-col overflow-hidden rounded-2xl border border-pokedex-border bg-pokedex-surface-2/60"
        >
          <div className="aspect-[3/4] w-full animate-pulse bg-pokedex-border/60" />
          <div className="flex flex-col gap-2 p-2.5 sm:p-3">
            <div className="h-3.5 w-4/5 animate-pulse rounded bg-pokedex-border/60" />
            <div className="h-3 w-2/5 animate-pulse rounded bg-pokedex-border/60" />
            <div className="mt-2 h-4 w-1/2 animate-pulse rounded bg-pokedex-border/60" />
          </div>
        </div>
      ))}
    </div>
  )
}

// Mirrors CardCarousel's single-slide footprint for the mobile loading state.
export function CardCarouselSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      <div className="mx-auto flex w-[86%] flex-col gap-3 rounded-2xl border border-pokedex-border bg-pokedex-surface-2/60 p-3">
        <div className="aspect-[3/4] w-full animate-pulse rounded-xl bg-pokedex-border/60" />
        <div className="flex flex-col gap-2">
          <div className="h-4 w-4/5 animate-pulse rounded bg-pokedex-border/60" />
          <div className="h-3 w-2/5 animate-pulse rounded bg-pokedex-border/60" />
          <div className="h-5 w-1/2 animate-pulse rounded bg-pokedex-border/60" />
        </div>
      </div>
      <div className="flex items-center justify-center gap-1.5">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="h-1.5 w-1.5 animate-pulse rounded-full bg-pokedex-border/60" />
        ))}
      </div>
    </div>
  )
}
