/** Shared visual system for the two "chrome" actions that bookend a screen
 * (back navigation, destructive delete): same height, type, geometry,
 * border treatment and hover glow -- only the color variant differs. Kept
 * out of Pokedex.tsx (component-only) so Fast Refresh isn't broken by a
 * plain-constant export sharing that file. */
export const pokedexButtonBase =
  'inline-flex items-center gap-2 border px-4 py-2 text-sm font-medium transition-all duration-200 [clip-path:polygon(8px_0,100%_0,100%_calc(100%-8px),calc(100%-8px)_100%,0_100%,0_8px)]'

export const pokedexButtonVariants = {
  neutral:
    'border-pokedex-border bg-pokedex-surface-2 text-pokedex-text hover:border-pokedex-red/50 hover:shadow-[0_0_12px_rgba(239,51,64,0.25)]',
  destructive:
    'border-pokedex-red/50 bg-pokedex-bg text-red-300 hover:border-pokedex-red hover:bg-pokedex-red-dark/25 hover:text-red-200 hover:shadow-[0_0_12px_rgba(239,51,64,0.35)]',
} as const
