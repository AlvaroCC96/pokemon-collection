import type { ReactNode } from 'react'

type LedColor = 'red' | 'yellow' | 'gold' | 'emerald' | 'muted'

const LED_COLORS: Record<LedColor, string> = {
  red: 'bg-pokedex-red shadow-[0_0_6px_rgba(227,53,53,0.7)]',
  yellow: 'bg-pokemon-yellow shadow-[0_0_6px_rgba(255,203,5,0.65)]',
  gold: 'bg-price-gold shadow-[0_0_6px_rgba(229,169,0,0.65)]',
  emerald: 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.65)]',
  muted: 'bg-pokedex-muted/40',
}

/** Small static "power light" -- a Pokedex-device detail, not an animation:
 * the glow is a fixed box-shadow, not a pulsing keyframe. */
export function Led({ color = 'red', className = '' }: { color?: LedColor; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${LED_COLORS[color]} ${className}`}
    />
  )
}

/** Device-panel-style section heading: a short accent tick + tracked-out
 * label, used instead of a plain uppercase caption on every panel. */
export function SectionLabel({ children, color = 'red' }: { children: ReactNode; color?: 'red' | 'gold' }) {
  return (
    <div className="flex items-center gap-2">
      <span
        aria-hidden="true"
        className={`h-3 w-1 rounded-full ${color === 'red' ? 'bg-pokedex-red/70' : 'bg-price-gold/70'}`}
      />
      <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-pokedex-muted">{children}</span>
    </div>
  )
}

/** Thin gradient bezel line used at the top of key panels for device-screen
 * identity -- the parent needs `overflow-hidden` to clip this bar's square
 * corners to its own rounded shape. */
export function ScanlineTopBar({ className = '' }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`h-[3px] w-full bg-gradient-to-r from-pokedex-red via-pokemon-yellow to-pokedex-red opacity-80 ${className}`}
    />
  )
}

/** Small "MODE" chip (COLLECTION MODE / SCAN MODE / CARD DATA) shown at the
 * top of a PokedexScreen -- purely a label, not a simulated device state. */
export function ModeTag({ children, led = 'red' }: { children: ReactNode; led?: LedColor }) {
  return (
    <div className="inline-flex w-fit items-center gap-1.5 rounded-full border border-pokedex-border bg-pokedex-surface-2 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-pokedex-muted">
      <Led color={led} />
      {children}
    </div>
  )
}

/** Outermost app chrome. Desktop gets a subtle red-bezel "casing" wrapping
 * the screen; mobile stays edge-to-edge (a thin top strip carries the
 * identity -- a full red border around a phone screen would waste width
 * that's needed for the carousel/forms). */
export function PokedexShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-pokedex-bg">
      <div className="h-1 w-full bg-gradient-to-r from-pokedex-red-dark via-pokedex-red to-pokedex-red-dark md:hidden" />
      <div className="mx-auto max-w-[1700px] md:px-4 md:py-5 lg:px-6">
        <div className="md:rounded-[28px] md:border md:border-pokedex-red-dark/50 md:bg-gradient-to-b md:from-pokedex-red-dark/10 md:via-pokedex-surface/60 md:to-pokedex-surface/60 md:p-3 md:shadow-2xl md:shadow-black/50 lg:p-4">
          {children}
        </div>
      </div>
    </div>
  )
}

/** LED cluster + title, used once per page inside PokedexShell. The blue
 * lens is the one deliberate spot of blue in the whole app -- reserved for
 * this "main sensor" detail, as requested. */
export function PokedexHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="flex items-center gap-3 px-4 py-4 md:px-2 md:pb-4 md:pt-1">
      <span
        aria-hidden="true"
        className="relative flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-sky-300 to-sky-600 shadow-[0_0_10px_rgba(56,189,248,0.55)]"
      >
        <span className="h-2.5 w-2.5 rounded-full bg-white/80" />
      </span>
      <span className="flex shrink-0 gap-1">
        <Led color="red" />
        <Led color="yellow" />
      </span>
      <div className="flex min-w-0 flex-col">
        <h1 className="truncate text-lg font-bold tracking-tight text-pokedex-text md:text-xl">{title}</h1>
        {subtitle && <p className="truncate text-xs text-pokedex-muted">{subtitle}</p>}
      </div>
    </header>
  )
}

/** The dark "screen" panel that holds actual page content -- the one
 * consistent inset look reused by Collection / Scan / Card Data. */
export function PokedexScreen({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-5 rounded-2xl border border-pokedex-border bg-pokedex-surface px-4 py-5 sm:px-6 sm:py-6">
      {children}
    </div>
  )
}
