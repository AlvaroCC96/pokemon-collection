import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import pokeballIcon from '../assets/icons/pokeball.svg'
import { pokedexButtonBase, pokedexButtonVariants } from './pokedexButtonStyles'

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
      <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-pokedex-muted">
        {children}
      </span>
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
    <div className="inline-flex w-fit items-center gap-1.5 rounded-full border border-pokedex-border bg-pokedex-surface-2 px-2.5 py-1 font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-pokedex-muted">
      <Led color={led} />
      {children}
    </div>
  )
}

/** Outermost app chrome: the graphite-and-grid backdrop every screen shares,
 * plus (desktop only) a slim red bezel wrapping the header+screen so the
 * whole page reads as "inside a device". Mobile skips the bezel -- it would
 * eat into width the carousel/forms need -- and gets its identity from the
 * header strip alone. */
export function PokedexShell({ children }: { children: ReactNode }) {
  return (
    <div className="pokedex-texture min-h-screen">
      <div className="mx-auto max-w-[1700px] md:px-4 md:py-5 lg:px-6">
        <div className="md:rounded-2xl md:border md:border-pokedex-border md:p-3 md:shadow-2xl md:shadow-black/60 lg:p-4">
          {children}
        </div>
      </div>
    </div>
  )
}

/** The header strip -- dark red/graphite HUD bar with the Pokeball mark,
 * a couple of decorative LEDs and a red bottom edge. Everything here is
 * decorative chrome, not new navigation: the only real links/actions live
 * inside PokedexScreen, same as before this redesign. */
export function PokedexHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="pokedex-hatch relative overflow-hidden rounded-2xl border border-pokedex-border bg-gradient-to-br from-pokedex-red-dark/25 via-pokedex-surface-2 to-pokedex-bg">
      <div className="pokedex-corner" aria-hidden="true" />
      <div className="flex items-center gap-3 px-4 py-4 sm:px-5">
        <img src={pokeballIcon} alt="" aria-hidden="true" className="h-9 w-9 shrink-0 drop-shadow-[0_0_6px_rgba(239,51,64,0.35)] sm:h-10 sm:w-10" />

        <div className="flex min-w-0 flex-1 flex-col">
          <h1 className="truncate text-lg font-bold tracking-tight text-pokedex-text sm:text-xl">{title}</h1>
          {subtitle && (
            <p className="truncate font-mono text-[10px] uppercase tracking-[0.2em] text-pokedex-muted">{subtitle}</p>
          )}
        </div>

        <span className="flex shrink-0 items-center gap-1.5">
          <Led color="red" />
          <Led color="yellow" />
          <span className="hidden h-6 w-px bg-pokedex-border sm:block" aria-hidden="true" />
          <span className="hidden font-mono text-[10px] uppercase tracking-[0.2em] text-pokedex-muted sm:inline">
            Database
          </span>
        </span>
      </div>
      <div className="h-[3px] w-full bg-gradient-to-r from-pokedex-red-dark via-pokedex-red to-pokedex-red-dark" />
    </header>
  )
}

/** The dark "screen" panel that holds actual page content -- the one
 * consistent inset look reused by Collection / Scan / Card Data. `relative`
 * so a page can pin a purely decorative HUD label (a ModeTag, a small
 * caption) to this panel's own corner via `absolute`, independent of the
 * padding its normal-flow content uses. */
export function PokedexScreen({ children }: { children: ReactNode }) {
  return (
    <div className="relative mt-3 flex flex-col gap-5 rounded-2xl border border-pokedex-border bg-pokedex-surface px-4 py-5 sm:px-6 sm:py-6">
      {children}
    </div>
  )
}

export function ArrowLeftIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 shrink-0" aria-hidden="true">
      <path
        d="M19 12H5M11 6l-6 6 6 6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 shrink-0" aria-hidden="true">
      <path
        d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m2 0-.7 12.1A2 2 0 0 1 15.3 21H8.7a2 2 0 0 1-2-1.9L6 7h12ZM10 11v6M14 11v6"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

/** "Volver a mi colección" -- same Link/navigation as before this pass,
 * just the Pokedex chrome-button treatment instead of a plain text link. */
export function BackLink({ to = '/', children = 'Volver a mi colección' }: { to?: string; children?: ReactNode }) {
  return (
    <Link to={to} className={`${pokedexButtonBase} ${pokedexButtonVariants.neutral}`}>
      <ArrowLeftIcon />
      {children}
    </Link>
  )
}
